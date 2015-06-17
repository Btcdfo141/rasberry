"""
homeassistant.components.device_tracker.tplink
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Device tracker platform that supports scanning a TP-Link router for device
presence.

Configuration:

To use the TP-Link tracker you will need to add something like the following
to your config/configuration.yaml

device_tracker:
  platform: tplink
  host: YOUR_ROUTER_IP
  username: YOUR_ADMIN_USERNAME
  password: YOUR_ADMIN_PASSWORD

Variables:

host
*Required
The IP address of your router, e.g. 192.168.1.1.

username
*Required
The username of an user with administrative privileges, usually 'admin'.

password
*Required
The password for your given admin account.

"""
import logging
from datetime import timedelta
import re
import threading
import requests

from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import validate_config
from homeassistant.util import Throttle
from homeassistant.components.device_tracker import DOMAIN

# Return cached results if last scan was less then this time ago
MIN_TIME_BETWEEN_SCANS = timedelta(seconds=5)

_LOGGER = logging.getLogger(__name__)


def get_scanner(hass, config):
    """ Validates config and returns a TP-Link scanner. """
    if not validate_config(config,
                           {DOMAIN: [CONF_HOST, CONF_USERNAME, CONF_PASSWORD]},
                           _LOGGER):
        return None

    scanner = TplinkDeviceScanner(config[DOMAIN])

    return scanner if scanner.success_init else None


class TplinkDeviceScanner(object):
    """ This class queries a wireless router running TP-Link firmware
    for connected devices.
    """

    def __init__(self, config):
        host = config[CONF_HOST]
        username, password = config[CONF_USERNAME], config[CONF_PASSWORD]

        self.parse_macs = re.compile('[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}-'+
                                     '[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}')

        self.host = host
        self.username = username
        self.password = password

        self.last_results = {}
        self.lock = threading.Lock()
        self.success_init = self._update_info()

    def scan_devices(self):
        """ Scans for new devices and return a
            list containing found device ids. """

        self._update_info()

        return self.last_results

    def get_device_name(self, device):
        """ The TP-Link firmware doesn't save the name of the wireless 
            device. """

        return None

    @Throttle(MIN_TIME_BETWEEN_SCANS)
    def _update_info(self):
        """ Ensures the information from the TP-Link router is up to date.
            Returns boolean if scanning successful. """

        with self.lock:
            _LOGGER.info("Loading wireless clients...")

            url = 'http://{}/userRpm/WlanStationRpm.htm'.format(self.host)
            referer = 'http://{}'.format(self.host)
            page = requests.get(url, auth=(self.username, self.password),
                                headers={'referer': referer})

            result = self.parse_macs.findall(page.text)

            if result:
                self.last_results = []
                for device_entry in result:
                    self.last_results.append(device_entry)

                return True

            return False
