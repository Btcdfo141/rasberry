"""
Support for Mycroft AI.
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/mycroft
"""

import logging

import voluptuous as vol

from homeassistant.helpers import discovery
from homeassistant.const import CONF_HOST
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['mycroftapi']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'mycroft'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string
    })
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up the Mycroft component."""
    hass.data[DOMAIN] = config[DOMAIN][CONF_HOST]

    return True
