"""The radiotherm component."""
from __future__ import annotations

from datetime import timedelta
import logging
from socket import timeout

from radiotherm.validate import RadiothermTstatError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_HOLD_TEMP, DOMAIN
from .data import (
    RadioThermData,
    RadioThermUpdate,
    async_get_data,
    async_get_device,
    async_get_name,
)

PLATFORMS: list[Platform] = [Platform.CLIMATE]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Radio Thermostat from a config entry."""
    host = entry.data[CONF_HOST]
    try:
        tstat = await async_get_device(hass, host)
        name = await async_get_name(hass, tstat)
    except RadiothermTstatError as ex:
        raise ConfigEntryNotReady(
            f"{host} was busy (invalid value returned): {ex}"
        ) from ex
    except timeout as ex:
        raise ConfigEntryNotReady(
            f"{host} timed out waiting for a response: {ex}"
        ) from ex

    async def _async_update() -> RadioThermUpdate:
        """Update data from the thermostat."""
        try:
            return await async_get_data(hass, tstat)
        except RadiothermTstatError as ex:
            raise UpdateFailed(
                f"{name} ({host}) was busy (invalid value returned): {ex}"
            ) from ex
        except timeout as ex:
            raise UpdateFailed(
                f"{name} ({host}) timed out waiting for a response: {ex}"
            ) from ex

    coordinator = DataUpdateCoordinator(
        hass=hass,
        logger=_LOGGER,
        name="radiothem {host}",
        update_interval=timedelta(seconds=15),
        update_method=_async_update,
    )
    await coordinator.async_config_entry_first_refresh()

    hold_temp = entry.data[CONF_HOLD_TEMP]
    hass.data[DOMAIN][entry.entry_id] = RadioThermData(
        coordinator, tstat, name, hold_temp
    )
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
