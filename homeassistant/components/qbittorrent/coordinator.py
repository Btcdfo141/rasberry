"""The QBittorrent coordinator."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from qbittorrent import Client
from qbittorrent.client import LoginRequired

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class QBittorrentDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for updating QBittorrent data."""

    def __init__(self, hass: HomeAssistant, client: Client) -> None:
        """Initialize coordinator."""
        self.client = client

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Async method to update QBittorrent data."""
        try:
            return await self.hass.async_add_executor_job(self.client.sync_main_data)
        except LoginRequired as exc:
            raise ConfigEntryError("Invalid authentication") from exc

    async def get_torrents(self, torrent_filter: str) -> list[dict[str, Any]]:
        """Async method to get QBittorrent torrents."""
        try:
            total_torrents = await self.hass.async_add_executor_job(
                lambda: self.client.torrents(filter=torrent_filter)
            )
        except LoginRequired as exc:
            raise ConfigEntryError("Invalid authentication") from exc

        return total_torrents
