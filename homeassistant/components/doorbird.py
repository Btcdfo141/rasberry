"""
Support for DoorBird device.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/doorbird/
"""
import asyncio
import logging

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_USERNAME, \
    CONF_PASSWORD, CONF_NAME
from homeassistant.components.http import HomeAssistantView
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['DoorBirdPy==0.1.3']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'doorbird'

API_URL = '/api/{}'.format(DOMAIN)

CONF_DOORBELL_EVENTS = 'doorbell_events'
CONF_CUSTOM_URL = 'hass_url_override'

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_DOORBELL_EVENTS): cv.boolean,
    vol.Optional(CONF_CUSTOM_URL): cv.string,
    vol.Optional(CONF_NAME): cv.string
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(
        cv.ensure_list,
        [DEVICE_SCHEMA]
    ),
}, extra=vol.ALLOW_EXTRA)

SENSOR_DOORBELL = 'doorbell'


def setup(hass, config):
    """Set up the DoorBird component."""
    from doorbirdpy import DoorBird

    doorstations = []

    for index, doorstation_config in enumerate(config[DOMAIN]):
        device_ip = doorstation_config.get(CONF_HOST)
        username = doorstation_config.get(CONF_USERNAME)
        password = doorstation_config.get(CONF_PASSWORD)
        name = (doorstation_config.get(CONF_NAME)
                or 'DoorBird {}'.format(index + 1))

        device = DoorBird(device_ip, username, password)
        status = device.ready()

        if status[0]:
            _LOGGER.info("Connected to DoorBird at %s as %s", device_ip,
                         username)
            doorstations.append(ConfiguredDoorbird(device, name))
        elif status[1] == 401:
            _LOGGER.error("Authorization rejected by DoorBird at %s",
                          device_ip)
            return False
        else:
            _LOGGER.error("Could not connect to DoorBird at %s: Error %s",
                          device_ip, str(status[1]))
            return False

        if doorstation_config.get(CONF_DOORBELL_EVENTS):
            # Provide an endpoint for the device to call to trigger events
            hass.http.register_view(DoorbirdRequestView())

            # Get the URL of this server
            hass_url = hass.config.api.base_url

            # Override if another is specified in the component configuration
            if doorstation_config.get(CONF_CUSTOM_URL):
                hass_url = doorstation_config.get(CONF_CUSTOM_URL)

            # This will make HA the only service that gets doorbell events
            url = '{}{}/{}/{}'.format(hass_url, API_URL, index + 1,
                                      SENSOR_DOORBELL)

            _LOGGER.info("DoorBird will connect to this instance via %s",
                         url)

            device.reset_notifications()
            device.subscribe_notification(SENSOR_DOORBELL, url)

    hass.data[DOMAIN] = doorstations

    return True


class ConfiguredDoorbird():
    """Attach additional information to pass along with configured device"""

    def __init__(self, device, name):
        """Initialize configured device"""
        self._name = name
        self._device = device

    @property
    def name(self):
        """Custom device name"""
        return self._name

    @property
    def device(self):
        """The configured device"""
        return self._device


class DoorbirdRequestView(HomeAssistantView):
    """Provide a page for the device to call."""

    requires_auth = False
    url = API_URL
    name = API_URL[1:].replace('/', ':')
    extra_urls = [API_URL + '/{index}/{sensor}']

    # pylint: disable=no-self-use
    @asyncio.coroutine
    def get(self, request, index, sensor):
        """Respond to requests from the device."""
        hass = request.app['hass']
        hass.bus.async_fire('{}_{}_{}'.format(DOMAIN, index, sensor))
        return 'OK'
