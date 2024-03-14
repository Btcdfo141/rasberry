"""Data coordinator for the dwd_weather_warnings integration."""

from __future__ import annotations

from dwdwfsapi import DwdWeatherWarningsAPI

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_REGION_DEVICE_TRACKER,
    CONF_REGION_IDENTIFIER,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
)
from .exceptions import EntityNotFoundError
from .util import get_position_data


class DwdWeatherWarningsCoordinator(DataUpdateCoordinator[None]):
    """Custom coordinator for the dwd_weather_warnings integration."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the dwd_weather_warnings coordinator."""
        super().__init__(
            hass, LOGGER, name=DOMAIN, update_interval=DEFAULT_SCAN_INTERVAL
        )

        self._api = None
        self._device_tracker = None

        # Do necessary setup of API when using a region identifier.
        if region_identifier := entry.data.get(CONF_REGION_IDENTIFIER):
            self._api = DwdWeatherWarningsAPI(region_identifier)
        else:
            self._device_tracker = entry.data.get(CONF_REGION_DEVICE_TRACKER)

    async def _async_update_data(self) -> None:
        """Get the latest data from the DWD Weather Warnings API."""
        if self._device_tracker:
            try:
                position = get_position_data(self.hass, self._device_tracker)
            except (EntityNotFoundError, AttributeError) as err:
                raise UpdateFailed(f"Error fetching position: {repr(err)}") from err

            self._api = await self.hass.async_add_executor_job(
                DwdWeatherWarningsAPI, position
            )
        else:
            if self._api is None:
                raise UpdateFailed("API is not initialized")

            await self.hass.async_add_executor_job(self._api.update)
