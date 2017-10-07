"""
Support for the EPH Controls Ember themostats.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/climate.ephember/
"""
import logging
from datetime import timedelta
import voluptuous as vol

from homeassistant.components.climate import (
    ClimateDevice, PLATFORM_SCHEMA, STATE_HEAT, STATE_IDLE)
from homeassistant.const import (
    TEMP_CELSIUS, CONF_USERNAME, CONF_PASSWORD)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['pyephember==0.0.3']

_LOGGER = logging.getLogger(__name__)

# Return cached results if last scan was less then this time ago
SCAN_INTERVAL = timedelta(seconds=120)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ephember thermostat."""
    from pyephember.pyephember import EphEmber

    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    try:
        ember = EphEmber(username, password)
        zones = ember.getZones()
        for zone in zones:
            add_devices([EphEmberThermostat(ember, zone)])
    except RuntimeError:
        _LOGGER.error("Cannot connect to EphEmber")
        return False

    return True


class EphEmberThermostat(ClimateDevice):
    """Representation of a HeatmiserV3 thermostat."""

    def __init__(self, ember, zone):
        """Initialize the thermostat."""
        self._ember = ember
        self._zone_name = zone['name']
        self._zone = zone
        self._hot_water = zone['isHotWater']

    @property
    def name(self):
        """Return the name of the thermostat, if any."""
        return self._zone_name

    @property
    def temperature_unit(self):
        """Return the unit of measurement which this thermostat uses."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._zone['currentTemperature']

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._zone['targetTemperature']

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        if self._zone['isCurrentlyActive']:
            return STATE_HEAT
        else:
            return STATE_IDLE

    @property
    def is_aux_heat_on(self):
        """Return true if aux heater."""
        return self._zone['isBoostActive']

    def turn_aux_heat_on(self):
        """Turn auxiliary heater on."""
        self._ember.activateBoostByZoneName(
            self._zone_name, self._zone['targetTemperature'])

    def turn_aux_heat_off(self):
        """Turn auxiliary heater off."""
        self._ember.deactivateBoostByZoneName(self._zone_name)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        return

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._zone['targetTemperature']

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._zone['targetTemperature']

    def update(self):
        """Get the latest data."""
        self._zone = self._ember.getZone(self._zone_name)
