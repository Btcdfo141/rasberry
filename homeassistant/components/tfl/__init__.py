"""The Transport for London integration."""
from __future__ import annotations

import logging

from tflwrapper import stopPoint
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .config_helper import config_from_entry
from .const import CONF_API_APP_KEY, CONF_STOP_POINTS, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

_STOP_POINT_SCHEME = vol.Schema({vol.Required(CONF_ID): cv.string})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_STOP_POINTS): [_STOP_POINT_SCHEME]}
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Transport for London from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    # conf = copy(entry.data)
    conf = config_from_entry(entry)

    stop_point_api = stopPoint(conf[CONF_API_APP_KEY])
    categories = await hass.async_add_executor_job(
        stop_point_api.getCategories
    )  # Check can call endpoint. TODO: Error handling
    _LOGGER.debug(
        "Setting up %s integration, got stoppoint categories %s", DOMAIN, categories
    )

    hass.data[DOMAIN][entry.entry_id] = stop_point_api
    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("update_listener called")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
