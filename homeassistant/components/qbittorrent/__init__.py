"""The qbittorrent component."""

import logging

from qbittorrent.client import LoginRequired
from requests.exceptions import RequestException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_ID,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, SERVICE_GET_TORRENTS, STATE_ATTR_TORRENT_INFO, TORRENT_FILTER
from .coordinator import QBittorrentDataCoordinator
from .helpers import format_torrents, setup_client

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up qBittorrent from a config entry."""

    try:
        client = await hass.async_add_executor_job(
            setup_client,
            config_entry.data[CONF_URL],
            config_entry.data[CONF_USERNAME],
            config_entry.data[CONF_PASSWORD],
            config_entry.data[CONF_VERIFY_SSL],
        )
    except LoginRequired as err:
        raise ConfigEntryNotReady("Invalid credentials") from err
    except RequestException as err:
        raise ConfigEntryNotReady("Failed to connect") from err
    coordinator = QBittorrentDataCoordinator(hass, client)

    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    async def handle_get_torrents(service_call: ServiceCall):
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get(service_call.data[ATTR_DEVICE_ID])

        if device_entry is None:
            return

        coordinator: QBittorrentDataCoordinator = hass.data[DOMAIN][
            config_entry.entry_id
        ]
        items = await coordinator.get_torrents(service_call.data[TORRENT_FILTER])
        info = format_torrents(items)
        return {
            STATE_ATTR_TORRENT_INFO: info,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_TORRENTS,
        handle_get_torrents,
        supports_response=SupportsResponse.ONLY,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload qBittorrent config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        del hass.data[DOMAIN][config_entry.entry_id]
        if not hass.data[DOMAIN]:
            del hass.data[DOMAIN]
    return unload_ok
