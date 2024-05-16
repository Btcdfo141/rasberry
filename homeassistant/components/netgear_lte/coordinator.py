"""Data update coordinator for the Netgear LTE integration."""

from __future__ import annotations

from datetime import timedelta

from eternalegypt.eternalegypt import Error, Information, Modem

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER


class NetgearLTEDataUpdateCoordinator(DataUpdateCoordinator[Information]):
    """Data update coordinator for the Netgear LTE integration."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        modem: Modem,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),
        )
        self.modem = modem

    async def _async_update_data(self) -> Information:
        """Get the latest data."""
        try:
            return await self.modem.information()
        except Error as ex:
            raise UpdateFailed(ex) from ex
