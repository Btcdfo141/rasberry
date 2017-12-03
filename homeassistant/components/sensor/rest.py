"""
Support for RESTful API sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.rest/
"""
import logging
import json

import voluptuous as vol
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_PAYLOAD, CONF_NAME, CONF_VALUE_TEMPLATE, CONF_METHOD, CONF_RESOURCE,
    CONF_UNIT_OF_MEASUREMENT, STATE_UNKNOWN, CONF_VERIFY_SSL, CONF_USERNAME,
    CONF_PASSWORD, CONF_AUTHENTICATION, HTTP_BASIC_AUTHENTICATION,
    HTTP_DIGEST_AUTHENTICATION, CONF_HEADERS)
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_METHOD = 'GET'
DEFAULT_NAME = 'REST Sensor'
DEFAULT_VERIFY_SSL = True

CONF_JSON_ATTRS = "json_attributes"
METHODS = ['POST', 'GET']

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_RESOURCE): cv.url,
    vol.Optional(CONF_AUTHENTICATION):
        vol.In([HTTP_BASIC_AUTHENTICATION, HTTP_DIGEST_AUTHENTICATION]),
    vol.Optional(CONF_HEADERS): {cv.string: cv.string},
    vol.Optional(CONF_METHOD, default=DEFAULT_METHOD): vol.In(METHODS),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_PAYLOAD): cv.string,
    vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    vol.Optional(CONF_USERNAME): cv.string,
    vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
    vol.Optional(CONF_JSON_ATTRS, default=[]): cv.ensure_list_csv,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the RESTful sensor."""
    name = config.get(CONF_NAME)
    resource = config.get(CONF_RESOURCE)
    method = config.get(CONF_METHOD)
    payload = config.get(CONF_PAYLOAD)
    verify_ssl = config.get(CONF_VERIFY_SSL)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    headers = config.get(CONF_HEADERS)
    unit = config.get(CONF_UNIT_OF_MEASUREMENT)
    value_template = config.get(CONF_VALUE_TEMPLATE)
    json_attrs = config.get(CONF_JSON_ATTRS)
    if value_template is not None:
        value_template.hass = hass

    if username and password:
        if config.get(CONF_AUTHENTICATION) == HTTP_DIGEST_AUTHENTICATION:
            auth = HTTPDigestAuth(username, password)
        else:
            auth = HTTPBasicAuth(username, password)
    else:
        auth = None
    rest = RestData(method, resource, auth, headers, payload, verify_ssl)
    rest.update()

    add_devices([RestSensor(hass, rest, name, unit,
                            value_template, json_attrs)], True)


class RestSensor(Entity):
    """Implementation of a REST sensor."""

    def __init__(self, hass, rest, name,
                 unit_of_measurement, value_template, json_attrs):
        """Initialize the REST sensor."""
        self._hass = hass
        self.rest = rest
        self._name = name
        self._state = STATE_UNKNOWN
        self._unit_of_measurement = unit_of_measurement
        self._value_template = value_template
        self._json_attrs = json_attrs
        self._attributes = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def available(self):
        """Return if the sensor data are available."""
        return self.rest.data is not None

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    def update(self):
        """Get the latest data from REST API and update the state."""
        self.rest.update()
        value = self.rest.data

        if self._json_attrs:
            self._attributes = {}
            try:
                json_dict = json.loads(value)
                if isinstance(json_dict, dict):
                    attrs = {k: json_dict[k] for k in self._json_attrs
                             if k in json_dict}
                    self._attributes = attrs
                else:
                    _LOGGER.warning('JSON result was not a dictionary')
            except ValueError:
                _LOGGER.warning('REST result could not be parsed as JSON')
                _LOGGER.debug('Erroneous JSON: %s', value)

        if value is None:
            value = STATE_UNKNOWN
        elif self._value_template is not None:
            value = self._value_template.render_with_possible_json_value(
                value, STATE_UNKNOWN)

        self._state = value

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes


class RestData(object):
    """Class for handling the data retrieval."""

    def __init__(self, method, resource, auth, headers, data, verify_ssl):
        """Initialize the data object."""
        self._request = requests.Request(
            method, resource, headers=headers, auth=auth, data=data).prepare()
        self._verify_ssl = verify_ssl
        self.data = None

    def update(self):
        """Get the latest data from REST service with provided method."""
        try:
            with requests.Session() as sess:
                response = sess.send(
                    self._request, timeout=10, verify=self._verify_ssl)

            self.data = response.text
        except requests.exceptions.RequestException:
            _LOGGER.error("Error fetching data: %s", self._request)
            self.data = None
