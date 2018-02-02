"""
Adds support for generic thermostat units.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/climate.generic_thermostat/
"""
import asyncio
import logging

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.core import DOMAIN as HA_DOMAIN
from homeassistant.components.climate import (
    STATE_HEAT, STATE_COOL, STATE_IDLE, STATE_AUTO, ClimateDevice,
    ATTR_OPERATION_MODE, ATTR_AWAY_MODE, SUPPORT_OPERATION_MODE,
    SUPPORT_AWAY_MODE, SUPPORT_TARGET_TEMPERATURE, PLATFORM_SCHEMA,
    SUPPORT_TARGET_TEMPERATURE_HIGH, SUPPORT_TARGET_TEMPERATURE_LOW,
    ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW)
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT, STATE_ON, STATE_OFF, ATTR_TEMPERATURE,
    CONF_NAME, ATTR_ENTITY_ID, SERVICE_TURN_ON, SERVICE_TURN_OFF,
    STATE_UNKNOWN)
from homeassistant.helpers import condition
from homeassistant.helpers.event import (
    async_track_state_change, async_track_time_interval)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import async_get_last_state

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['switch', 'sensor']

DEFAULT_TOLERANCE = 0.3
DEFAULT_NAME = 'Generic Thermostat'
DEFAULT_TARGET_TEMP_HIGH = 21
DEFAULT_TARGET_TEMP_LOW = 18

CONF_HEATER_CONTROL = 'heater_control'
CONF_SENSOR = 'target_sensor'
CONF_MIN_TEMP = 'min_temp'
CONF_MAX_TEMP = 'max_temp'
CONF_TARGET_TEMP = 'target_temp'
CONF_TARGET_TEMP_HIGH = 'target_temp_high'
CONF_TARGET_TEMP_LOW = 'target_temp_low'
CONF_AC_CONTROL = 'ac_control'
CONF_MIN_DUR = 'min_cycle_duration'
CONF_COLD_TOLERANCE = 'cold_tolerance'
CONF_HOT_TOLERANCE = 'hot_tolerance'
CONF_KEEP_ALIVE = 'keep_alive'
CONF_INITIAL_OPERATION_MODE = 'initial_operation_mode'
CONF_AWAY_TEMP_COOL = 'away_temp_cool'
CONF_AWAY_TEMP_HEAT = 'away_temp_heat'
SUPPORT_FLAGS = (SUPPORT_OPERATION_MODE)

PLATFORM_SCHEMA = vol.All(PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_HEATER_CONTROL): cv.entity_id,
    vol.Optional(CONF_AC_CONTROL): cv.entity_id,
    vol.Required(CONF_SENSOR): cv.entity_id,
    vol.Optional(CONF_MAX_TEMP): vol.Coerce(float),
    vol.Optional(CONF_MIN_DUR): vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_MIN_TEMP): vol.Coerce(float),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_COLD_TOLERANCE, default=DEFAULT_TOLERANCE): vol.Coerce(
        float),
    vol.Optional(CONF_HOT_TOLERANCE, default=DEFAULT_TOLERANCE): vol.Coerce(
        float),
    vol.Exclusive(CONF_TARGET_TEMP, "temperature"): vol.Coerce(float),
    vol.Inclusive(CONF_TARGET_TEMP_HIGH, "temperature"): vol.Coerce(float),
    vol.Inclusive(CONF_TARGET_TEMP_LOW, "temperature"): vol.Coerce(float),
    vol.Optional(CONF_KEEP_ALIVE): vol.All(
        cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_INITIAL_OPERATION_MODE):
        vol.In([STATE_AUTO, STATE_HEAT, STATE_COOL, STATE_OFF]),
    vol.Optional(CONF_AWAY_TEMP_COOL): vol.Coerce(float),
    vol.Optional(CONF_AWAY_TEMP_HEAT): vol.Coerce(float)
}), cv.has_at_least_one_key(CONF_AC_CONTROL, CONF_HEATER_CONTROL))


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the generic thermostat platform."""
    name = config.get(CONF_NAME)
    heater_entity_id = config.get(CONF_HEATER_CONTROL)
    ac_entity_id = config.get(CONF_AC_CONTROL)
    sensor_entity_id = config.get(CONF_SENSOR)
    min_temp = config.get(CONF_MIN_TEMP)
    max_temp = config.get(CONF_MAX_TEMP)
    target_temp = config.get(CONF_TARGET_TEMP)
    target_temp_high = config.get(CONF_TARGET_TEMP_HIGH)
    target_temp_low = config.get(CONF_TARGET_TEMP_LOW)
    min_cycle_duration = config.get(CONF_MIN_DUR)
    cold_tolerance = config.get(CONF_COLD_TOLERANCE)
    hot_tolerance = config.get(CONF_HOT_TOLERANCE)
    keep_alive = config.get(CONF_KEEP_ALIVE)
    initial_operation_mode = config.get(CONF_INITIAL_OPERATION_MODE)
    away_temp_cool = config.get(CONF_AWAY_TEMP_COOL)
    away_temp_heat = config.get(CONF_AWAY_TEMP_HEAT)

    async_add_devices([GenericThermostat(
        hass, name, heater_entity_id, sensor_entity_id, min_temp, max_temp,
        target_temp, ac_entity_id, min_cycle_duration, cold_tolerance,
        hot_tolerance, keep_alive, initial_operation_mode, away_temp_cool,
        away_temp_heat, target_temp_high, target_temp_low)])


class GenericThermostat(ClimateDevice):
    """Representation of a Generic Thermostat device."""

    def __init__(self, hass, name, heater_entity_id, sensor_entity_id,
                 min_temp, max_temp, target_temp, ac_entity_id,
                 min_cycle_duration, cold_tolerance, hot_tolerance,
                 keep_alive, initial_operation_mode, away_temp_cool,
                 away_temp_heat, target_temp_high, target_temp_low):
        """Initialize the thermostat."""
        self.hass = hass
        self._name = name
        self.heater_entity_id = heater_entity_id
        self.ac_entity_id = ac_entity_id
        self.min_cycle_duration = min_cycle_duration
        self._cold_tolerance = cold_tolerance
        self._hot_tolerance = hot_tolerance
        self._keep_alive = keep_alive
        self._operation_list = [STATE_OFF]
        self._support_flags = SUPPORT_FLAGS
        self._saved_target_temp_high = target_temp
        self._target_temp_high = target_temp
        self._saved_target_temp_low = target_temp
        self._target_temp_low = target_temp

        if ac_entity_id:
            self._operation_list.append(STATE_COOL)

        if heater_entity_id:
            self._operation_list.append(STATE_HEAT)

        if ac_entity_id and heater_entity_id:
            _LOGGER.debug("Thermostat supports AUTO mode")
            self._support_flags = self._support_flags | \
                SUPPORT_TARGET_TEMPERATURE_HIGH | \
                SUPPORT_TARGET_TEMPERATURE_LOW
            self._operation_list.append(STATE_AUTO)
            self._saved_target_temp_high = target_temp_high
            self._saved_target_temp_low = target_temp_low
            self._target_temp_high = target_temp_high
            self._target_temp_low = target_temp_low
        else:
            _LOGGER.debug("Thermostat supports just target temperature")
            self._support_flags = self._support_flags | \
                SUPPORT_TARGET_TEMPERATURE

        if away_temp_heat is not None or away_temp_cool is not None:
            self._support_flags = self._support_flags | SUPPORT_AWAY_MODE

        self._current_operation = initial_operation_mode
        self._cur_temp = None
        self._min_temp = min_temp
        self._max_temp = max_temp
        self._unit = hass.config.units.temperature_unit
        self._away_temp_cool = away_temp_cool
        self._away_temp_heat = away_temp_heat
        self._is_away = False

        sensor_state = hass.states.get(sensor_entity_id)
        if sensor_state and sensor_state.state != STATE_UNKNOWN:
            self._async_update_temp(sensor_state)

        async_track_state_change(
            hass, sensor_entity_id, self._async_sensor_changed)
        if heater_entity_id:
            async_track_state_change(
                hass, heater_entity_id, self._async_switch_changed)
        if ac_entity_id:
            async_track_state_change(
                hass, ac_entity_id, self._async_switch_changed)

        if self._keep_alive:
            async_track_time_interval(
                hass, self._async_keep_alive, self._keep_alive)

        sensor_state = hass.states.get(sensor_entity_id)
        if sensor_state and sensor_state.state != STATE_UNKNOWN:
            self._async_update_temp(sensor_state)

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Run when entity about to be added."""
        # Check If we have an old state
        old_state = yield from async_get_last_state(self.hass,
                                                    self.entity_id)
        if old_state is not None:
            if STATE_AUTO in self.operation_list:
                if old_state.attributes.get(ATTR_TARGET_TEMP_LOW) \
                        is not None:
                    if self._target_temp_low is None:
                        self._target_temp_low = \
                            float(old_state.attributes[ATTR_TARGET_TEMP_LOW])

                if old_state.attributes.get(ATTR_TARGET_TEMP_HIGH) \
                        is not None:
                    if self._target_temp_high is None:
                        self._target_temp_high = \
                            float(old_state.attributes[ATTR_TARGET_TEMP_HIGH])
            else:
                if old_state.attributes.get(ATTR_TEMPERATURE) is not None:
                    if self._target_temp_low is None:
                        self._target_temp_low = \
                            float(old_state.attributes[ATTR_TEMPERATURE])
                    if self._target_temp_high is None:
                        self._target_temp_high = \
                            float(old_state.attributes[ATTR_TEMPERATURE])

            # Restore _is_away
            if old_state.attributes.get(ATTR_AWAY_MODE) is not None:
                self._is_away = str(
                    old_state.attributes[ATTR_AWAY_MODE]) == STATE_ON

            # Restore _current_operation from previous value
            if (self._current_operation is None and
                    old_state.attributes.get(ATTR_OPERATION_MODE)
                    is not None):
                self._current_operation = \
                    old_state.attributes[ATTR_OPERATION_MODE]

        # Fill value with defaults if not found in old_state
        if self._target_temp_high is None:
            self._target_temp_high = DEFAULT_TARGET_TEMP_HIGH
        if self._target_temp_low is None:
            self._target_temp_low = DEFAULT_TARGET_TEMP_LOW
        if self._saved_target_temp_high is None:
            self._saved_target_temp_high = DEFAULT_TARGET_TEMP_HIGH
        if self._saved_target_temp_low is None:
            self._saved_target_temp_low = DEFAULT_TARGET_TEMP_LOW
        if self._current_operation not in self.operation_list:
            self.set_operation_mode(STATE_OFF)

        if STATE_AUTO in self.operation_list and \
                (self._target_temp_low + self._hot_tolerance >=
                 self._target_temp_high - self._cold_tolerance):
            _LOGGER.error("Low and high too close."
                          "Unpredictable results with %s - %s",
                          self._target_temp_low, self.target_temperature_high)

    @property
    def state(self):
        """Return the current state."""
        if self.current_operation == STATE_OFF:
            return STATE_OFF
        if self.is_on:
            if self.current_operation == STATE_AUTO:
                if self._is_heating and self._is_cooling:
                    # Emergency shut off
                    _LOGGER.error("Both heat and cool on, turning off")
                    self.set_operation_mode(STATE_OFF)
                if self._is_heating:
                    return STATE_HEAT
                if self._is_cooling:
                    return STATE_COOL
            else:
                return self.current_operation
        else:
            return STATE_IDLE

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def current_temperature(self):
        """Return the sensor temperature."""
        return self._cur_temp

    @property
    def current_operation(self):
        """Return current operation."""
        return self._current_operation

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        if STATE_AUTO in self.operation_list:
            return None
        if self.ac_entity_id:
            return self._target_temp_high
        if self.heater_entity_id:
            return self._target_temp_low

    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        if STATE_AUTO not in self.operation_list:
            return None
        return self._target_temp_high

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        if STATE_AUTO not in self.operation_list:
            return None
        return self._target_temp_low

    @property
    def operation_list(self):
        """List of available operation modes."""
        return self._operation_list

    async def async_set_operation_mode(self, operation_mode):
        """Set operation mode."""
        if operation_mode == STATE_OFF:
            self._current_operation = operation_mode
            if self._is_heating:
                self._heater_turn_off()
            if self._is_cooling:
                self._ac_turn_off()
        elif operation_mode in self.operation_list:
            self._current_operation = operation_mode
            self._async_control_thermostat()
        else:
            _LOGGER.error("Unrecognized operation mode: %s", operation_mode)
            return
        self.schedule_update_ha_state()

    @asyncio.coroutine
    def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        if STATE_AUTO in self.operation_list:
            if kwargs.get(ATTR_TARGET_TEMP_HIGH) is not None and \
                    kwargs.get(ATTR_TARGET_TEMP_LOW) is not None:
                self._target_temp_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
                self._target_temp_low = kwargs.get(ATTR_TARGET_TEMP_LOW)
        else:
            if kwargs.get(ATTR_TEMPERATURE) is not None:
                self._target_temp_high = kwargs.get(ATTR_TEMPERATURE)
                self._target_temp_low = kwargs.get(ATTR_TEMPERATURE)
        self._async_control_thermostat()
        yield from self.async_update_ha_state()

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        # pylint: disable=no-member
        if self._min_temp:
            return self._min_temp

        # get default temp from super class
        return super().min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        # pylint: disable=no-member
        if self._max_temp:
            return self._max_temp

        # Get default temp from super class
        return super().max_temp

    @asyncio.coroutine
    def _async_sensor_changed(self, entity_id, old_state, new_state):
        """Handle temperature changes."""
        if new_state is None:
            return

        self._async_update_temp(new_state)
        self._async_control_thermostat()
        yield from self.async_update_ha_state()

    @callback
    def _async_switch_changed(self, entity_id, old_state, new_state):
        """Handle switch state changes."""
        if new_state is None:
            return
        self.async_schedule_update_ha_state()

    @callback
    def _async_keep_alive(self, time):
        """Call at constant intervals for keep-alive purposes."""
        if self._is_heating:
            self._heater_turn_on()
        else:
            self._heater_turn_off()
        if self._is_cooling:
            self._ac_turn_on()
        else:
            self._ac_turn_off()

    @callback
    def _async_update_temp(self, state):
        """Update thermostat with latest state from sensor."""
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

        try:
            self._cur_temp = self.hass.config.units.temperature(
                float(state.state), unit)
        except ValueError as ex:
            _LOGGER.error("Unable to update from sensor: %s", ex)

    @callback
    def _async_control_thermostat(self):
        """Check if we need to turn heating on or off."""
        if None in (self._cur_temp,
                    self._target_temp_high, self._target_temp_low):
            _LOGGER.debug("Could not obtain current and target temperatures. "
                          "Generic thermostat inactive.")
            return

        if self.current_operation == STATE_OFF:
            return
        if self.min_cycle_duration:
            if self.ac_entity_id:
                if self._is_cooling:
                    current_state = STATE_ON
                else:
                    current_state = STATE_OFF
                long_enough = condition.state(
                    self.hass, self.ac_entity_id, current_state,
                    self.min_cycle_duration)
                if not long_enough:
                    _LOGGER.debug("Thermostat state changed too rapidly. "
                                  "Cancelling current cooling change.")
                    return
            if self.heater_entity_id:
                if self._is_heating:
                    current_state = STATE_ON
                else:
                    current_state = STATE_OFF
                long_enough = condition.state(
                    self.hass, self.heater_entity_id, current_state,
                    self.min_cycle_duration)
                if not long_enough:
                    _LOGGER.debug("Thermostat state changed too rapidly. "
                                  "Cancelling current heating change.")
                    return

        if self.ac_entity_id:
            target_temp = self._target_temp_high
            if self._is_cooling:
                too_cold = target_temp - self._cur_temp >= \
                    self._cold_tolerance
                if too_cold:
                    self._ac_turn_off()
            else:
                too_hot = self._cur_temp - target_temp >= \
                    self._hot_tolerance
                if too_hot:
                    self._ac_turn_on()
        if self.heater_entity_id:
            target_temp = self._target_temp_low
            if self._is_heating:
                too_hot = self._cur_temp - target_temp >= \
                    self._hot_tolerance
                if too_hot:
                    self._heater_turn_off()
            else:
                too_cold = target_temp - self._cur_temp >= \
                    self._cold_tolerance
                if too_cold:
                    self._heater_turn_on()

    @property
    def is_on(self):
        """Return true if any device is currently active."""
        return self._is_heating or self._is_cooling

    @property
    def _is_heating(self):
        """Return true if toggleable heating device is currently active."""
        if self.heater_entity_id:
            return self.hass.states.is_state(self.heater_entity_id, STATE_ON)
        else:
            return False

    @property
    def _is_cooling(self):
        """Return true if toggleable cooling device is currently active."""
        if self.ac_entity_id:
            return self.hass.states.is_state(self.ac_entity_id, STATE_ON)
        else:
            return False

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @callback
    def _heater_turn_on(self):
        """Turn heater toggleable device on."""
        if self.heater_entity_id:
            data = {ATTR_ENTITY_ID: self.heater_entity_id}
            _LOGGER.info('Turning on heater %s', self.heater_entity_id)
            self.hass.async_add_job(
                self.hass.services.async_call(HA_DOMAIN,
                                              SERVICE_TURN_ON, data))

    @callback
    def _ac_turn_on(self):
        """Turn A/C toggleable device on."""
        if self.ac_entity_id:
            data = {ATTR_ENTITY_ID: self.ac_entity_id}
            _LOGGER.info('Turning on AC %s', self.heater_entity_id)
            self.hass.async_add_job(
                self.hass.services.async_call(HA_DOMAIN,
                                              SERVICE_TURN_ON, data))

    @callback
    def _heater_turn_off(self):
        """Turn heater toggleable device off."""
        if self.heater_entity_id:
            data = {ATTR_ENTITY_ID: self.heater_entity_id}
            _LOGGER.info('Turning off heater %s', self.heater_entity_id)
            self.hass.async_add_job(
                self.hass.services.async_call(HA_DOMAIN,
                                              SERVICE_TURN_OFF, data))

    @callback
    def _ac_turn_off(self):
        """Turn A/C toggleable device off."""
        if self.ac_entity_id:
            data = {ATTR_ENTITY_ID: self.ac_entity_id}
            _LOGGER.info('Turning off AC %s', self.heater_entity_id)
            self.hass.async_add_job(
                self.hass.services.async_call(HA_DOMAIN,
                                              SERVICE_TURN_OFF, data))

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        return self._is_away

    def turn_away_mode_on(self):
        """Turn away mode on by setting it on away hold indefinitely."""
        _LOGGER.info('Turning on away mode')
        self._is_away = True
        self._saved_target_temp_low = self._target_temp_low
        self._target_temp_low = self._away_temp_heat
        self._saved_target_temp_high = self._target_temp_high
        self._target_temp_high = self._away_temp_cool
        self._async_control_thermostat()
        self.schedule_update_ha_state()

    def turn_away_mode_off(self):
        """Turn away off."""
        _LOGGER.info('Turning off away mode')
        self._is_away = False
        self._target_temp_high = self._saved_target_temp_high
        self._target_temp_low = self._saved_target_temp_low
        self._async_control_thermostat()
        self.schedule_update_ha_state()
