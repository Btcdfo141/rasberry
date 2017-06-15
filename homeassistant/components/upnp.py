"""
This module will attempt to open a port in your router for Home Assistant.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/upnp/
"""
import logging
from urllib.parse import urlsplit

import voluptuous as vol

from homeassistant.const import (EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['api']
DOMAIN = 'upnp'

CONF_ENABLE_PORT_MAPPING = 'port_mapping'
DEFAULT_PORT_MAPPING = 'true'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_ENABLE_PORT_MAPPING, default=True): cv.boolean,
    }),
}, extra=vol.ALLOW_EXTRA)


# pylint: disable=import-error, no-member, broad-except
def setup(hass, config):
    """Register a port mapping for Home Assistant via UPnP."""
    import miniupnpc

    upnp = miniupnpc.UPnP()

    upnp.discoverdelay = 200
    upnp.discover()
    try:
        upnp.selectigd()
    except Exception:
        _LOGGER.exception("Error when attempting to discover an UPnP IGD")
        return False

    base_url = urlsplit(hass.config.api.base_url)
    host = base_url.hostname
    external_port = internal_port = base_url.port

    port_mapping = config[DOMAIN].get(CONF_ENABLE_PORT_MAPPING, DEFAULT_PORT_MAPPING)
    if port_mapping: 
        upnp.addportmapping(
            external_port, 'TCP', host, internal_port, 'Home Assistant', '')

        def deregister_port(event):
            """De-register the UPnP port mapping."""
            upnp.deleteportmapping(hass.config.api.port, 'TCP')

        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, deregister_port)

    return True
