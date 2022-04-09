"""Data update coordinator for the Lidarr integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta

from aiopyarr import (
    LidarrQueue,
    LidarrWantedCutoff,
    RootFolder,
    SystemStatus,
    exceptions,
)
from aiopyarr.lidarr_client import LidarrClient
from aiopyarr.models.host_configuration import PyArrHostConfiguration

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_MAX_RECORDS, DOMAIN, LOGGER


class LidarrDataUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator for the Lidarr integration."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        host_configuration: PyArrHostConfiguration,
        api_client: LidarrClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.api_client = api_client
        self.commands: int = 0
        self.disk_space: list[RootFolder] = []
        self.host_configuration = host_configuration
        self.queue: LidarrQueue = LidarrQueue({"records": []})
        self.system_status: SystemStatus = SystemStatus({"": ""})
        self.wanted: LidarrWantedCutoff = LidarrWantedCutoff({"records": []})

    async def _async_update_data(self) -> None:
        """Get the latest data from Lidarr."""
        records = self.config_entry.options[CONF_MAX_RECORDS]
        try:
            [
                commands,
                self.disk_space,
                self.queue,
                self.system_status,
                self.wanted,
            ] = await asyncio.gather(
                *[
                    self.api_client.async_get_commands(),
                    self.api_client.async_get_root_folders(),
                    self.api_client.async_get_queue(page_size=records),
                    self.api_client.async_get_system_status(),
                    self.api_client.async_get_wanted(page_size=records),
                ]
            )

        except exceptions.ArrConnectionException as ex:
            raise UpdateFailed(ex) from ex
        except exceptions.ArrAuthenticationException as ex:
            raise ConfigEntryAuthFailed(
                "API Key is no longer valid. Please reauthenticate"
            ) from ex
        self.commands = len({c.name: c.status for c in commands})
