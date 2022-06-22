"""Support for Aqara Smart devices."""
from __future__ import annotations

import logging
from typing import NamedTuple

from aqara_iot import (
    AqaraDeviceListener,
    AqaraDeviceManager,
    AqaraHomeManager,
    AqaraOpenAPI,
    AqaraOpenMQ,
    AqaraPoint,
)
import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send

from .const import (
    AQARA_DISCOVERY_NEW,
    AQARA_HA_SIGNAL_REGISTER_POINT,
    AQARA_HA_SIGNAL_UPDATE_ENTITY,
    AQARA_HA_SIGNAL_UPDATE_POINT_VALUE,
    CONF_COUNTRY_CODE,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    PLATFORMS,
)
from .util import string_dot_to_underline, string_underline_to_dot

_LOGGER = logging.getLogger(__name__)


class HomeAssistantAqaraData(NamedTuple):
    """Aqara data stored in the Home Assistant data object."""

    device_listener: DeviceListener
    device_manager: AqaraDeviceManager
    home_manager: AqaraHomeManager
    aqara_mqtt_client: AqaraOpenMQ


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Async setup hass config entry."""
    hass.data.setdefault(DOMAIN, {})

    api = AqaraOpenAPI(country_code=entry.data[CONF_COUNTRY_CODE])

    try:
        response = await hass.async_add_executor_job(
            api.get_auth,
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            "",
        )
    except requests.exceptions.RequestException as err:
        raise ConfigEntryNotReady(err) from err

    if response is not True:
        raise ConfigEntryNotReady("api.get_auth error")

    device_manager = AqaraDeviceManager(api)

    home_manager = AqaraHomeManager(api, device_manager)

    mqtt_client = AqaraOpenMQ()
    mqtt_client.set_get_config(device_manager.config_mqtt_add)
    mqtt_client.add_message_listener(device_manager.on_message)
    mqtt_client.start()

    listener = DeviceListener(hass, device_manager)
    device_manager.add_device_listener(listener)

    hass.data[DOMAIN][entry.entry_id] = HomeAssistantAqaraData(
        device_listener=listener,
        device_manager=device_manager,
        home_manager=home_manager,
        aqara_mqtt_client=mqtt_client,
    )

    # Get devices & clean up device entities
    await hass.async_add_executor_job(home_manager.update_device_cache)
    await hass.async_add_executor_job(home_manager.update_location_info)
    await cleanup_device_registry(hass, device_manager)

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def cleanup_device_registry(
    hass: HomeAssistant, device_manager: AqaraDeviceManager
) -> None:
    """Remove deleted device registry entry if there are no remaining entities."""
    device_registry = dr.async_get(hass)
    for dev_id, device_entry in list(device_registry.devices.items()):
        for item in device_entry.identifiers:
            if (
                DOMAIN == item[0]
                and device_manager.get_point(string_underline_to_dot(item[1])) is None
            ):
                device_registry.async_remove_device(dev_id)
                break


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unloading the Aqara platforms."""
    unload = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload:
        hass_data: HomeAssistantAqaraData = hass.data[DOMAIN][entry.entry_id]
        hass_data.aqara_mqtt_client.stop()
        hass_data.device_manager.remove_device_listener(hass_data.device_listener)

        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload


class DeviceListener(AqaraDeviceListener):
    """Device Update Listener."""

    def __init__(
        self,
        hass: HomeAssistant,
        device_manager: AqaraDeviceManager,
    ) -> None:
        """Init DeviceListener."""
        self.hass = hass
        self.device_manager = device_manager
        self.point_ids: set[str] = set()
        self.device_registry = dr.async_get(hass)
        self.nouse_point_ids: set[str] = set()
        async_dispatcher_connect(
            self.hass,
            AQARA_HA_SIGNAL_REGISTER_POINT,
            self.async_register_point,
        )

    def async_register_point(self, point_id):
        """Add point id to point_ids."""
        self.point_ids.add(point_id)

    def update_device(self, aqara_point: AqaraPoint) -> None:
        """Update device status."""
        if string_dot_to_underline(aqara_point.id) in self.point_ids:
            _LOGGER.debug(
                "Received update for device %s: %s",
                aqara_point.id,
                self.device_manager.device_map[aqara_point.did].point_map[
                    aqara_point.id
                ],
            )
            dispatcher_send(
                self.hass,
                f"{AQARA_HA_SIGNAL_UPDATE_POINT_VALUE}_{string_dot_to_underline(aqara_point.id)}",
                aqara_point,
            )
            dispatcher_send(
                self.hass,
                f"{AQARA_HA_SIGNAL_UPDATE_ENTITY}_{string_dot_to_underline(aqara_point.id)}",
            )

    def add_device(self, aqara_point: AqaraPoint) -> None:
        """Add device added listener."""
        # Ensure the device isn't present stale
        self.hass.add_job(
            self.async_remove_device, string_dot_to_underline(aqara_point.id)
        )

        self.point_ids.add(aqara_point.id)

        # the point.did not point.id
        dispatcher_send(self.hass, AQARA_DISCOVERY_NEW, [aqara_point.did])

    def remove_device(self, point_id: str) -> None:
        """Add device removed listener."""
        self.hass.add_job(self.async_remove_device, string_dot_to_underline(point_id))

    @callback
    def async_remove_device(self, hass_device_id: str) -> None:
        """Remove device from Home Assistant."""
        _LOGGER.debug("Remove device: %s", hass_device_id)

        device_entry = self.device_registry.async_get_device(
            identifiers={(DOMAIN, hass_device_id)}
        )
        if device_entry is not None:
            self.device_registry.async_remove_device(device_entry.id)
            self.point_ids.discard(string_underline_to_dot(hass_device_id))
            self.nouse_point_ids.discard(string_underline_to_dot(hass_device_id))
