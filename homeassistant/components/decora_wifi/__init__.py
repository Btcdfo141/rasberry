"""Support for the myLeviton decora_wifi component."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .common import CommFailed, DecoraWifiPlatform, LoginFailed
from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Decora Wifi from a config entry."""

    conf_data = entry.data
    email = conf_data[CONF_USERNAME]
    password = conf_data[CONF_PASSWORD]

    try:
        session = await DecoraWifiPlatform.async_setup_decora_wifi(
            hass,
            email,
            password,
        )
    except LoginFailed as exc:
        raise ConfigEntryAuthFailed from exc
    except CommFailed as exc:
        raise ConfigEntryNotReady from exc
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = session

    # Forward the config entry to each platform which has devices to set up.
    hass.config_entries.async_setup_platforms(entry, session.active_platforms)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    session: DecoraWifiPlatform = hass.data[DOMAIN].get(entry.entry_id, None)
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    if session:
        try:
            # Attempt to log out.
            await hass.async_add_executor_job(session.teardown)
        except CommFailed:
            _LOGGER.debug(
                "Communication with myLeviton failed while attempting to logout"
            )
    hass.data[DOMAIN].pop(entry.entry_id)

    return True
