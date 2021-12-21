"""The sensibo component."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sensibo from a config entry."""
    title = entry.title

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    _LOGGER.debug("Loaded entry for %s", title)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Sensibo config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    title = entry.title
    if unload_ok:
        _LOGGER.debug("Unloaded entry for %s", title)
        return unload_ok

    return False
