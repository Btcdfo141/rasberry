"""The Modern Forms integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from aiomodernforms import (
    ModernFormsConnectionError,
    ModernFormsDevice,
    ModernFormsError,
)
from aiomodernforms.models import Device

from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_MODEL, ATTR_NAME, ATTR_SW_VERSION, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import ATTR_IDENTIFIERS, ATTR_MANUFACTURER, DOMAIN

SCAN_INTERVAL = timedelta(seconds=5)
PLATFORMS = [
    FAN_DOMAIN,
]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Modern Forms device from a config entry."""

    # Create Modern Forms instance for this entry
    coordinator = ModernFormsDataUpdateCoordinator(hass, host=entry.data[CONF_HOST])
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    if entry.unique_id is None:
        hass.config_entries.async_update_entry(
            entry, unique_id=coordinator.data.info.mac_address
        )

    # Set up all platforms for this device/entry.
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Modern Forms config entry."""

    # Unload entities for this entry/device.
    unload_ok = all(
        await asyncio.gather(
            *(
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            )
        )
    )

    if unload_ok:
        del hass.data[DOMAIN][entry.entry_id]

    if not hass.data[DOMAIN]:
        del hass.data[DOMAIN]

    return unload_ok


def modernforms_exception_handler(func):
    """Decorate Modern Forms calls to handle Modern Forms exceptions.

    A decorator that wraps the passed in function, catches Modern Forms errors,
    and handles the availability of the device in the data coordinator.
    """

    async def handler(self, *args, **kwargs):
        try:
            await func(self, *args, **kwargs)
            self.coordinator.update_listeners()

        except ModernFormsConnectionError as error:
            _LOGGER.error("Error communicating with API: %s", error)
            self.coordinator.last_update_success = False
            self.coordinator.update_listeners()

        except ModernFormsError as error:
            _LOGGER.error("Invalid response from API: %s", error)

    return handler


class ModernFormsDataUpdateCoordinator(DataUpdateCoordinator[Device]):
    """Class to manage fetching Modern Forms data from single endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        host: str,
    ) -> None:
        """Initialize global Modern Forms data updater."""
        self.modernforms = ModernFormsDevice(
            host, session=async_get_clientsession(hass)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    def update_listeners(self) -> None:
        """Call update on all listeners."""
        for update_callback in self._listeners:
            update_callback()

    async def _async_update_data(self) -> ModernFormsDevice:
        """Fetch data from Modern Forms."""
        try:
            return await self.modernforms.update(
                full_update=not self.last_update_success
            )
        except ModernFormsError as error:
            raise UpdateFailed(f"Invalid response from API: {error}") from error


class ModernFormsEntity(CoordinatorEntity[ModernFormsDataUpdateCoordinator]):
    """Defines a base Modern Forms entity."""

    def __init__(
        self,
        *,
        entry_id: str,
        coordinator: ModernFormsDataUpdateCoordinator,
        name: str,
        icon: str,
        enabled_default: bool = True,
    ) -> None:
        """Initialize the Modern Forms entity."""
        super().__init__(coordinator)
        self._attr_enabled_default = enabled_default
        self._entry_id = entry_id
        self._attr_icon = icon
        self._attr_name = name
        self._unsub_dispatcher = None


class ModernFormsDeviceEntity(ModernFormsEntity):
    """Defines a Modern Forms device entity."""

    coordinator: ModernFormsDataUpdateCoordinator

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Modern Forms device."""
        return {
            ATTR_IDENTIFIERS: {(DOMAIN, self.coordinator.data.info.mac_address)},  # type: ignore
            ATTR_NAME: self.coordinator.data.info.device_name,
            ATTR_MANUFACTURER: "Modern Forms",
            ATTR_MODEL: self.coordinator.data.info.fan_type,
            ATTR_SW_VERSION: f"{self.coordinator.data.info.firmware_version} / {self.coordinator.data.info.main_mcu_firmware_version}",
        }
