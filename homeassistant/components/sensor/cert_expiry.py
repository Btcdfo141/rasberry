"""Counts the days an HTTPS (TLS) certificate will expire (days).

Example configuration.yaml:

  sensor:
    - platform: cert_expiry
      server_name: home-assistant.io

For more details about this sensor please refer to the
documentation at https://home-assistant.io/components/sensor.cert_expiry
"""
import logging
import ssl
import socket
import datetime
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity

REQUIREMENTS = []
_LOGGER = logging.getLogger(__name__)

CONF_SERVER_NAME = 'server_name'
CONF_SERVER_PORT = 'server_port'
ICON = 'mdi:certificate'

MIN_TIME_BETWEEN_UPDATES = datetime.timedelta(hours=12)
TIMEOUT = 10

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SERVER_NAME): cv.string,
    vol.Optional(CONF_SERVER_PORT, default=443): cv.port,
    })


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup certificate expiry sensor."""
    server_name = config.get(CONF_SERVER_NAME)
    server_port = config.get(CONF_SERVER_PORT)
    add_devices([SSLCertificate(server_name, server_port)])


class SSLCertificate(Entity):
    """Implements certificate expiry sensor."""

    def __init__(self, server_name, server_port):
        """Initialize the sensor."""
        self.server_name = server_name
        self.server_port = server_port
        self._name = "{} cert expiry".format(server_name)
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return 'days'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return ICON

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Fetch certificate information."""
        try:
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(socket.socket(),
                                   server_hostname=self.server_name)
            sock.connect((self.server_name, self.server_port))
        except Exception as e:
            _LOGGER.error('Cannot connect to %s' % (self.server_name))
            raise e

        try:
            cert = sock.getpeercert()
        except Exception as e:
            _LOGGER.error('Cannot fetch certificate from %s' %
                          (self.server_name))
            raise e

        timestamp = ssl.cert_time_to_seconds(cert['notAfter'])
        ts = datetime.datetime.fromtimestamp(timestamp)
        expiry = ts - datetime.datetime.today()
        self._state = expiry.days
