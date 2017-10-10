"""
Support for eQ-3 Bluetooth Smart thermostats.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/climate.eq3btsmart/
"""
import logging

import voluptuous as vol

from homeassistant.components.climate import (
    ClimateDevice, PLATFORM_SCHEMA, PRECISION_HALVES,
    STATE_AUTO, STATE_ON, STATE_OFF,
)
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change
from homeassistant.const import (
    CONF_MAC, TEMP_CELSIUS, CONF_DEVICES, ATTR_TEMPERATURE,
    STATE_UNKNOWN)

import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['python-eq3bt==0.1.6']

_LOGGER = logging.getLogger(__name__)

STATE_BOOST = 'boost'
STATE_AWAY = 'away'
STATE_MANUAL = 'manual'

ATTR_STATE_WINDOW_OPEN = 'window_open'
ATTR_STATE_VALVE = 'valve'
ATTR_STATE_LOCKED = 'is_locked'
ATTR_STATE_LOW_BAT = 'low_battery'
ATTR_STATE_AWAY_END = 'away_end'

CONF_TEMPERATURE_SENSOR = 'sensor'

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_MAC): cv.string,
    vol.Optional(CONF_TEMPERATURE_SENSOR): cv.entity_id,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES):
        vol.Schema({cv.string: DEVICE_SCHEMA}),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the eQ-3 BLE thermostats."""
    devices = []

    for name, device_cfg in config[CONF_DEVICES].items():
        mac = device_cfg[CONF_MAC]
        temperature_sensor = device_cfg.get(CONF_TEMPERATURE_SENSOR)

        thermostat = EQ3BTSmartThermostat(mac, name, temperature_sensor)
        devices.append(thermostat)

        if temperature_sensor is not None:
            async_track_state_change(hass, [temperature_sensor],
                                     thermostat.temperature_state_changed)

    add_devices(devices)


# pylint: disable=import-error
class EQ3BTSmartThermostat(ClimateDevice):
    """Representation of a eQ-3 Bluetooth Smart thermostat."""

    def __init__(self, _mac, _name, _sensor):
        """Initialize the thermostat."""
        # we want to avoid name clash with this module..
        import eq3bt as eq3

        self.modes = {eq3.Mode.Open: STATE_ON,
                      eq3.Mode.Closed: STATE_OFF,
                      eq3.Mode.Auto: STATE_AUTO,
                      eq3.Mode.Manual: STATE_MANUAL,
                      eq3.Mode.Boost: STATE_BOOST,
                      eq3.Mode.Away: STATE_AWAY}

        self.reverse_modes = {v: k for k, v in self.modes.items()}

        self._name = _name
        self._thermostat = eq3.Thermostat(_mac)
        self._temperature_sensor = _sensor
        self._sensor_temperature = STATE_UNKNOWN

    @property
    def available(self) -> bool:
        """Return if thermostat is available."""
        return self.current_operation is not None

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement that is used."""
        return TEMP_CELSIUS

    @property
    def precision(self):
        """Return eq3bt's precision 0.5."""
        return PRECISION_HALVES

    @callback
    def temperature_state_changed(self, entity_id, _, new_state):
        """Update the temperature status.

        This callback is triggered, when the sensor state changes.
        """
        new_value = new_state.state

        if new_value != STATE_UNKNOWN:
            # Force 0.5 precision from the temperature sensor
            new_value = round(float(new_value) * 2) / 2

        self._sensor_temperature = new_value

    @property
    def current_temperature(self):
        """If no sensor is specified, just return target_temperature."""
        if self._temperature_sensor is not None:
            return self._sensor_temperature

        return self.target_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._thermostat.target_temperature

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._thermostat.target_temperature = temperature

    @property
    def current_operation(self):
        """Return the current operation mode."""
        if self._thermostat.mode < 0:
            return None
        return self.modes[self._thermostat.mode]

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return [x for x in self.modes.values()]

    def set_operation_mode(self, operation_mode):
        """Set operation mode."""
        self._thermostat.mode = self.reverse_modes[operation_mode]

    def turn_away_mode_off(self):
        """Away mode off turns to AUTO mode."""
        self.set_operation_mode(STATE_AUTO)

    def turn_away_mode_on(self):
        """Set away mode on."""
        self.set_operation_mode(STATE_AWAY)

    @property
    def is_away_mode_on(self):
        """Return if we are away."""
        return self.current_operation == STATE_AWAY

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._thermostat.min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._thermostat.max_temp

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        dev_specific = {
            ATTR_STATE_LOCKED: self._thermostat.locked,
            ATTR_STATE_LOW_BAT: self._thermostat.low_battery,
            ATTR_STATE_VALVE: self._thermostat.valve_state,
            ATTR_STATE_WINDOW_OPEN: self._thermostat.window_open,
            ATTR_STATE_AWAY_END: self._thermostat.away_end,
        }

        return dev_specific

    def update(self):
        """Update the data from the thermostat."""
        from bluepy.btle import BTLEException
        try:
            self._thermostat.update()
        except BTLEException as ex:
            _LOGGER.warning("Updating the state failed: %s", ex)
