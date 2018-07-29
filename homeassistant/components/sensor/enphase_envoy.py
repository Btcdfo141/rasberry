"""
Support for Enphase Envoy solar energy monitor.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.enphase_envoy/
"""

import logging
import voluptuous as vol
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv


REQUIREMENTS = ['envoy_reader==0.1']
_LOGGER = logging.getLogger(__name__)

CONF_IP_ADDRESS = 'ip'
CONF_MONITORED_CONDITIONS = 'monitored_conditions'
DEFAULT_NAMES = [
    "Envoy Current Energy Production",
    "Envoy Today's Energy Production",
    "Envoy Last Seven Days Energy Production",
    "Envoy Lifetime Energy Production",
    "Envoy Current Energy Consumption",
    "Envoy Today's Energy Consumption",
    "Envoy Last Seven Days Energy Consumption",
    "Envoy Lifetime Energy Consumption"]

SENSOR_TYPES = [
    "production", "daily_production", "7_days_production",
    "lifetime_production", "consumption", "daily_consumption",
    "7_days_consumption", "lifetime_consumption"]

ICON = 'mdi:flash'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Optional(CONF_MONITORED_CONDITIONS): vol.All(cv.ensure_list)

})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Enphase Envoy sensor."""
    ip_address = config.get(CONF_IP_ADDRESS)
    monitored_conditions = config.get(CONF_MONITORED_CONDITIONS, {})

# Iterate through the list of sensors, adding it if either monitored
# conditions has been left out of the config, or that the given sensor
# is in the monitored conditions list
    for i in range(8):
        if monitored_conditions == {} or \
                    SENSOR_TYPES[i] in monitored_conditions:
            add_devices([Envoy(ip_address, DEFAULT_NAMES[i],
                               SENSOR_TYPES[i])], True)


class Envoy(Entity):
    """Implementation of the Enphase Envoy sensors."""

    def __init__(self, ip_address, name, sensor_type):
        """Initialize the sensor."""
        self._ip_address = ip_address
        self._name = name
        if sensor_type == 'production' or sensor_type == 'consumption':
            self._unit_of_measurement = 'W'
        else:
            self._unit_of_measurement = "Wh"

        self._type = sensor_type
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return ICON

    def update(self):
        """Get the energy production data from the Enphase Envoy."""
        import envoy_reader

        if self._type == "production":
            self._state = int(envoy_reader.production(self._ip_address))
        elif self._type == "daily_production":
            self._state = int(envoy_reader.daily_production(self._ip_address))
        elif self._type == "7_days_production":
            self._state = int(envoy_reader.seven_days_production(
                              self._ip_address))
        elif self._type == "lifetime_production":
            self._state = int(envoy_reader.lifetime_production(
                              self._ip_address))

        elif self._type == "consumption":
            self._state = int(envoy_reader.consumption(self._ip_address))
        elif self._type == "daily_consumption":
            self._state = int(envoy_reader.daily_consumption(
                              self._ip_address))
        elif self._type == "7_days_consumption":
            self._state = int(envoy_reader.seven_days_consumption(
                              self._ip_address))
        elif self._type == "lifetime_consumption":
            self._state = int(envoy_reader.lifetime_consumption(
                              self._ip_address))
