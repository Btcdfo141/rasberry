"""Data coordinator for the dwd_weather_warnings integration."""

from __future__ import annotations

from dwdwfsapi import DwdWeatherWarningsAPI

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_GPS_TRACKER, DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER
from .util import get_position_data


class DwdWeatherWarningsCoordinator(DataUpdateCoordinator[None]):
    """Custom coordinator for the dwd_weather_warnings integration."""

    def __init__(self, hass: HomeAssistant, api: DwdWeatherWarningsAPI) -> None:
        """Initialize the dwd_weather_warnings coordinator."""
        super().__init__(
            hass, LOGGER, name=DOMAIN, update_interval=DEFAULT_SCAN_INTERVAL
        )

        self.api = api

    async def _async_update_data(self) -> None:
        """Get the latest data from the DWD Weather Warnings API."""
        if self.config_entry is not None:
            if gps_tracker := self.config_entry.data.get(CONF_GPS_TRACKER, None):
                position = get_position_data(self.hass, gps_tracker)
                self.api = await self.hass.async_add_executor_job(
                    DwdWeatherWarningsAPI, position
                )
            else:
                await self.hass.async_add_executor_job(self.api.update)
