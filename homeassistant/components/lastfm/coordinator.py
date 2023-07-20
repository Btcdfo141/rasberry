"""DataUpdateCoordinator for the LastFM integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from pylast import LastFMNetwork, PyLastError, Track

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_USERS,
    DOMAIN,
    LOGGER,
)


@dataclass
class LastFMUserData:
    """Data holder for LastFM data."""

    play_count: int
    image: str
    now_playing: Track | None
    top_track: Track | None
    last_track: Track | None


class LastFMDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, LastFMUserData | None]]
):
    """A LastFM Data Update Coordinator."""

    config_entry: ConfigEntry
    _client: LastFMNetwork

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the LastFM data coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self._client = LastFMNetwork(api_key=self.config_entry.options[CONF_API_KEY])

    async def _async_update_data(self) -> dict[str, LastFMUserData | None]:
        res = {}
        for username in self.config_entry.options[CONF_USERS]:
            res[username] = await self.hass.async_add_executor_job(
                self._get_user_data, username
            )
        return res

    def _get_user_data(self, username: str) -> LastFMUserData | None:
        user = self._client.get_user(username)
        try:
            play_count = user.get_playcount()
            image = user.get_image()
            now_playing = user.get_now_playing()
            top_tracks = user.get_top_tracks(limit=1)
            top_track = None
            if len(top_tracks) > 0:
                top_track = top_tracks[0].item
            last_tracks = user.get_recent_tracks(limit=1)
            last_track = None
            if len(last_tracks) > 0:
                last_track = last_tracks[0].track
            return LastFMUserData(
                play_count,
                image,
                now_playing,
                top_track,
                last_track,
            )
        except PyLastError as exc:
            LOGGER.error("Failed to load LastFM user `%s`: %r", username, exc)
            return None
