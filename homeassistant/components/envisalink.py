"""
Support for Envisalink devices.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/envisalink/
"""
import logging
from homeassistant.const import (
    ATTR_SERVICE, ATTR_DISCOVERED,
    EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP, EVENT_PLATFORM_DISCOVERED)
from homeassistant.helpers.entity import Entity
from homeassistant.components.discovery import load_platform
from homeassistant.util import convert

REQUIREMENTS = ['pyenvisalink==0.2', 'pydispatcher==2.0.5']

_LOGGER = logging.getLogger(__name__)
DOMAIN = 'envisalink'

EVL_CONTROLLER = None

CONF_EVL_HOST = 'host'
CONF_EVL_PORT = 'port'
CONF_PANEL_TYPE = 'panel_type'
CONF_EVL_VERSION = 'evl_version'
CONF_USERNAME = 'user_name'
CONF_PASS = 'password'
CONF_EVL_KEEPALIVE = 'keepalive_interval'
CONF_ZONEDUMP_INTERVAL = 'zonedump_interval'
CONF_ZONES = 'zones'
CONF_PARTITIONS = 'partitions'

DEFAULT_PORT = 4025
DEFAULT_EVL_VERSION = 3
DEFAULT_KEEPALIVE = 60
DEFAULT_ZONEDUMP_INTERVAL = 30

SIGNAL_ZONE_UPDATE = 'zones_updated'
SIGNAL_PARTITION_UPDATE = 'partition_updated'

# pylint: disable=unused-argument, too-many-function-args
def setup(hass, base_config):
    """Common setup for Envisalink devices."""
    from pyenvisalink import EnvisalinkAlarmPanel
    from pydispatch import dispatcher

    global EVL_CONTROLLER

    config = base_config.get(DOMAIN)

    if config.get(CONF_EVL_HOST) is None:
        _LOGGER.error(str.format("Missing required variable: {0}", CONF_EVL_HOST))
        return False

    if config.get(CONF_PANEL_TYPE) is None:
        _LOGGER.error(str.format("Missing required variable: {0}. Valid values are HONEYWELL/DSC.", CONF_PANEL_TYPE))
        return False

    if config.get(CONF_USERNAME) is None:
        _LOGGER.error(str.format("Missing required variable: {0}", CONF_USERNAME))
        return False

    if config.get(CONF_PASS) is None:
        _LOGGER.error(str.format("Missing required variable: {0}", CONF_PASS))
        return False

    if config.get(CONF_ZONES) is None:
        _LOGGER.error(str.format("Missing required variable: {0}", CONF_ZONES))
        return False

    if config.get(CONF_PARTITIONS) is None:
        _LOGGER.error(str.format("Missing required variable: {0}", CONF_PARTITIONS))
        return False

    _host = config.get(CONF_EVL_HOST)
    _port = convert(config.get(CONF_EVL_PORT), int, DEFAULT_PORT)
    _panelType = config.get(CONF_PANEL_TYPE)
    _version = convert(config.get(CONF_EVL_VERSION), int, DEFAULT_EVL_VERSION)
    _user = config.get(CONF_USERNAME)
    _pass = config.get(CONF_PASS)
    _keepAlive = convert(config.get(CONF_EVL_KEEPALIVE), int, DEFAULT_KEEPALIVE)
    _zoneDump = convert(config.get(CONF_ZONEDUMP_INTERVAL), int, DEFAULT_ZONEDUMP_INTERVAL)
    _zones = config.get(CONF_ZONES)
    _partitions = config.get(CONF_PARTITIONS)

    EVL_CONTROLLER = EnvisalinkAlarmPanel(_host, _port, _panelType, _version, _user, _pass, _zoneDump, _keepAlive)

    def zones_updated_callback(data):
        """This will handle zone timer updates. Basically just an update of all zones."""
        _LOGGER.info("Envisalink sent a zone update event.  Updating zones...")
        dispatcher.send(signal=SIGNAL_ZONE_UPDATE, sender=None)

    def stop_envisalink(event):
        """Shutdown envisalink connection and thread on exit."""
        _LOGGER.info("Shutting down envisalink.")
        EVL_CONTROLLER.stop()

    def start_envisalink(event):
        """Startup process for the envisalink."""
        EVL_CONTROLLER.start()
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_envisalink)

    EVL_CONTROLLER.callback_zone_timer_dump = zones_updated_callback
    EVL_CONTROLLER.callback_zone_state_change = zones_updated_callback 
    start_envisalink(None) 

    # Load sub-components for envisalink
    for comp_name in (['binary_sensor', 'alarm_control_panel']):
        load_platform(hass, comp_name, 'envisalink',
                      {'zones': _zones, 'partitions': _partitions}, config)

    return True


class EnvisalinkDevice(Entity):
    """Representation of an envisalink devicetity."""

    def __init__(self, name, info, controller):
        """Initialize the device."""
        self._controller = controller
        self._info = info
        self._name = name

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed."""
        return False
