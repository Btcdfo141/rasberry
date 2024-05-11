"""DataUpdateCoordinator for solarlog integration."""

from datetime import datetime, timedelta
import logging
from urllib.parse import ParseResult, urlparse

from solarlog_cli.solarlog_connector import SolarLogConnector
from solarlog_cli.solarlog_exceptions import (
    SolarLogConnectionError,
    SolarLogUpdateError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import update_coordinator

_LOGGER = logging.getLogger(__name__)


class SolarlogData(update_coordinator.DataUpdateCoordinator):
    """Get and update the latest data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the data object."""
        super().__init__(
            hass, _LOGGER, name="SolarLog", update_interval=timedelta(seconds=60)
        )

        host_entry = entry.data[CONF_HOST]

        url = urlparse(host_entry, "http")
        netloc = url.netloc or url.path
        path = url.path if url.netloc else ""
        url = ParseResult("http", netloc, path, *url[3:])
        self.unique_id = entry.entry_id
        self.name = entry.title
        self.host = url.geturl()

        extended_data = entry.data["extended_data"]

        self.solarlog = SolarLogConnector(
            self.host, extended_data, hass.config.time_zone
        )
        self._attr_last_update_success = None

    async def _async_update_data(self):
        """Update the data from the SolarLog device."""
        _LOGGER.debug("Start data update")

        try:
            data = await self.solarlog.update_data()
        except SolarLogConnectionError as err:
            raise ConfigEntryNotReady(err) from err
        except SolarLogUpdateError as err:
            raise update_coordinator.UpdateFailed(err) from err

        self._attr_last_update_success = datetime.now()

        _LOGGER.debug("Data successfully updated")

        return data
