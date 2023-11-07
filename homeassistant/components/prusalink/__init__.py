"""The PrusaLink integration."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from datetime import timedelta
import logging
from time import monotonic
from typing import Generic, TypeVar

from pyprusalink import JobInfo, LegacyPrinterStatus, PrinterStatus, PrusaLink
from pyprusalink.types import InvalidAuth, PrusaLinkError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.CAMERA, Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PrusaLink from a config entry."""
    api = PrusaLink(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    coordinators = {
        "legacy_status": LegacyStatusCoordinator(hass, api),
        "status": StatusCoordinator(hass, api),
        "job": JobUpdateCoordinator(hass, api),
    }
    for coordinator in coordinators.values():
        await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        config_entry.version = 2
        data = dict(config_entry.data)
        # "maker" is currently hardcoded in the firmware
        # https://github.com/prusa3d/Prusa-Firmware-Buddy/blob/bfb0ffc745ee6546e7efdba618d0e7c0f4c909cd/lib/WUI/wui_api.h#L19
        data[CONF_USERNAME] = "maker"
        data[CONF_PASSWORD] = config_entry.data[CONF_API_KEY]
        data.pop(CONF_API_KEY)
        hass.config_entries.async_update_entry(config_entry, data=data)
        _LOGGER.info("Migrated config entry to version %d", config_entry.version)

    return True


T = TypeVar("T", PrinterStatus, LegacyPrinterStatus, JobInfo)


class PrusaLinkUpdateCoordinator(DataUpdateCoordinator, Generic[T], ABC):
    """Update coordinator for the printer."""

    config_entry: ConfigEntry
    expect_change_until = 0.0

    def __init__(self, hass: HomeAssistant, api: PrusaLink) -> None:
        """Initialize the update coordinator."""
        self.api = api

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=self._get_update_interval(None)
        )

    async def _async_update_data(self) -> T:
        """Update the data."""
        try:
            async with asyncio.timeout(5):
                data = await self._fetch_data()
        except InvalidAuth:
            raise UpdateFailed("Invalid authentication") from None
        except PrusaLinkError as err:
            raise UpdateFailed(str(err)) from err

        self.update_interval = self._get_update_interval(data)
        return data

    @abstractmethod
    async def _fetch_data(self) -> T:
        """Fetch the actual data."""
        raise NotImplementedError

    @callback
    def expect_change(self) -> None:
        """Expect a change."""
        self.expect_change_until = monotonic() + 30

    def _get_update_interval(self, data: T) -> timedelta:
        """Get new update interval."""
        if self.expect_change_until > monotonic():
            return timedelta(seconds=5)

        return timedelta(seconds=30)


class StatusCoordinator(PrusaLinkUpdateCoordinator[PrinterStatus]):
    """Printer update coordinator."""

    async def _fetch_data(self) -> PrinterStatus:
        """Fetch the printer data."""
        return await self.api.get_status()


class LegacyStatusCoordinator(PrusaLinkUpdateCoordinator[LegacyPrinterStatus]):
    """Printer legacy update coordinator."""

    async def _fetch_data(self) -> LegacyPrinterStatus:
        """Fetch the printer data."""
        return await self.api.get_legacy_printer()


class JobUpdateCoordinator(PrusaLinkUpdateCoordinator[JobInfo]):
    """Job update coordinator."""

    async def _fetch_data(self) -> JobInfo:
        """Fetch the printer data."""
        return await self.api.get_job()


class PrusaLinkEntity(CoordinatorEntity[PrusaLinkUpdateCoordinator]):
    """Defines a base PrusaLink entity."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this PrusaLink device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name=self.coordinator.config_entry.title,
            manufacturer="Prusa",
            configuration_url=self.coordinator.api.client.host,
        )
