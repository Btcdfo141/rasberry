"""Support for the Skybell HD Doorbell."""
from __future__ import annotations

import logging

from aioskybell import Skybell
from aioskybell.device import SkybellDevice
from aioskybell.exceptions import SkybellAuthenticationException, SkybellException
import voluptuous as vol

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR
from homeassistant.components.camera import DOMAIN as CAMERA
from homeassistant.components.light import DOMAIN as LIGHT
from homeassistant.components.sensor import DOMAIN as SENSOR
from homeassistant.components.skybell.const import (
    ATTRIBUTION,
    DATA_COORDINATOR,
    DATA_DEVICES,
    DEFAULT_CACHEDB,
    DEFAULT_NAME,
    DOMAIN,
    MIN_TIME_BETWEEN_UPDATES,
)
from homeassistant.components.switch import DOMAIN as SWITCH
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_USERNAME,
    __version__,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    vol.All(
        # Deprecated in Home Assistant 2022.3
        cv.deprecated(DOMAIN),
        {
            DOMAIN: vol.Schema(
                {
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            )
        },
    ),
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = [BINARY_SENSOR, CAMERA, LIGHT, SENSOR, SWITCH]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the SkyBell component."""
    hass.data.setdefault(DOMAIN, {})

    entry_config = {}
    if DOMAIN not in config:
        return True
    for parameter in config[DOMAIN]:
        if parameter == CONF_USERNAME:
            entry_config[CONF_EMAIL] = config[DOMAIN][parameter]
        else:
            entry_config[parameter] = config[DOMAIN][parameter]
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=entry_config,
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Skybell from a config entry."""
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    api = Skybell(
        username=email,
        password=password,
        get_devices=True,
        cache_path=hass.config.path(DEFAULT_CACHEDB),
        session=async_get_clientsession(hass),
    )
    try:
        devices = await api.async_initialize()
    except SkybellAuthenticationException as ex:
        raise ConfigEntryAuthFailed(
            f"Authentication Error: please check credentials: {ex}"
        ) from ex
    except SkybellException as ex:
        raise ConfigEntryNotReady(f"Unable to connect to Skybell service: {ex}") from ex

    async def async_update_data() -> None:
        """Fetch data from API endpoint."""
        try:
            [await device.async_update() for device in devices]
        except SkybellException as err:
            raise UpdateFailed(f"Failed to communicate with device: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        name=DEFAULT_NAME,
        update_method=async_update_data,
        update_interval=MIN_TIME_BETWEEN_UPDATES,
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_DEVICES: devices,
    }

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class SkybellEntity(CoordinatorEntity):
    """An HA implementation for Skybell devices."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device: SkybellDevice,
        server_unique_id: str,
    ) -> None:
        """Initialize a SkyBell entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_device_info = DeviceInfo(
            connections={(dr.CONNECTION_NETWORK_MAC, device.mac)},
            identifiers={
                (DOMAIN, f"{server_unique_id}-{device.serial_no}")
            },
            manufacturer=DEFAULT_NAME,
            model=device.type,
            name=device.name,
            sw_version=device.firmware_ver,
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "device_id": self._device.device_id,
            "status": self._device.status,
            "location": self._device.location,
            "wifi_ssid": self._device.wifi_ssid,
            "wifi_status": self._device.wifi_status,
            "last_check_in": self._device.last_check_in,
            "motion_threshold": self._device.motion_threshold,
            "video_profile": self._device.video_profile,
        }

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return super().available and self._device.wifi_status != "offline"
