"""
Platform for the iZone AC.

For more details about this component, please refer to the documentation
https://home-assistant.io/components/izone/
"""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EXCLUDE
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .constants import DOMAIN, DATA_CONFIG
from .discovery import (
    async_start_discovery_service, async_stop_discovery_service)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(
            CONF_EXCLUDE, default=[]
        ): vol.All(cv.ensure_list, [cv.string]),
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistantType, config: ConfigType):
    """Register the iZone component config."""
    conf = config.get(DOMAIN)
    if not conf:
        return True

    hass.data[DATA_CONFIG] = conf

    # Explicitly added in the config file, create a config entry.
    hass.async_add_job(hass.config_entries.flow.async_init(
        DOMAIN, context={'source': config_entries.SOURCE_IMPORT}))

    return True


async def async_setup_entry(hass, entry):
    """Set up from a config entry."""
    await async_start_discovery_service(hass)

    hass.async_add_job(
        hass.config_entries.async_forward_entry_setup(
            entry, 'climate'))
    return True


async def async_unload_entry(hass, entry):
    """Unload the config entry and stop discovery process."""
    await async_stop_discovery_service(hass)
    return True
