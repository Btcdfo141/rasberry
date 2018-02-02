"""The tests for the generic_thermostat."""
import asyncio
import datetime
import unittest
from unittest import mock
import pytz

import homeassistant.core as ha
from homeassistant.core import callback, CoreState, State
from homeassistant.setup import setup_component, async_setup_component
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_OFF,
    STATE_IDLE,
    TEMP_CELSIUS,
    ATTR_TEMPERATURE
)
from homeassistant import loader
from homeassistant.util.unit_system import METRIC_SYSTEM
from homeassistant.util.async_ import run_coroutine_threadsafe
from homeassistant.components import climate, input_boolean, switch
import homeassistant.components as comps
from tests.common import (assert_setup_component, get_test_home_assistant,
                          mock_restore_cache)


ENTITY = 'climate.test'
ENT_SENSOR = 'sensor.test'
ENT_SWITCH_HEAT = 'switch.test_heat'
ENT_SWITCH_AC = 'switch.test_ac'
ATTR_AWAY_MODE = 'away_mode'
MIN_TEMP = 3.0
MAX_TEMP = 65.0
TARGET_TEMP = 42.0
COLD_TOLERANCE = 0.3
HOT_TOLERANCE = 0.3

DEFAULT_MIN_TEMP = 7.0
DEFAULT_MAX_TEMP = 35.0
DEFAULT_AWAY_TEMP_COOL = 30.0
DEFAULT_AWAY_TEMP_HEAT = 16.0
DEFAULT_TARGET_TEMP_HIGH = 21.0
DEFAULT_TARGET_TEMP_LOW = 18.0


class TestSetupClimateGenericThermostat(unittest.TestCase):
    """Test the Generic thermostat with custom config."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_setup_missing_conf(self):
        """Test set up heat_control with missing config values."""
        config = {
            'name': 'test'
        }
        with assert_setup_component(0):
            setup_component(self.hass, 'climate', {
                'climate': config})

    def test_setup_valid_conf(self):
        """Test set up generic_thermostat with valid config values."""
        self.assertTrue(
            setup_component(self.hass, 'climate',
                            {'climate': {
                                'platform': 'generic_thermostat',
                                'name': 'test',
                                'heater_control': ENT_SWITCH_HEAT,
                                'target_sensor': ENT_SENSOR
                                }})
        )

    @mock.patch('logging.Logger.error')
    def test_setup_valid_conf_with_error(self, log_mock):
        """Test set up generic_thermostat with valid config values."""
        self.assertTrue(
            setup_component(self.hass, 'climate',
                            {'climate': {
                                'platform': 'generic_thermostat',
                                'name': 'test',
                                'target_temp_high': 21.1,
                                'target_temp_low': 21,
                                'heater_control': ENT_SWITCH_HEAT,
                                'ac_control': ENT_SWITCH_AC,
                                'target_sensor': ENT_SENSOR
                                }})
        )
        self.assertEqual(log_mock.call_count, 1)


class TestGenericThermostatHeaterSwitching(unittest.TestCase):
    """Test the Generic thermostat heater switching.

    Different toggle type devices are tested.
    """

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.units = METRIC_SYSTEM
        self.assertTrue(run_coroutine_threadsafe(
            comps.async_setup(self.hass, {}), self.hass.loop
        ).result())

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_heater_input_boolean(self):
        """Test heater switching input_boolean."""
        heater_switch = 'input_boolean.test'
        assert setup_component(self.hass, input_boolean.DOMAIN,
                               {'input_boolean': {'test': None}})

        assert setup_component(self.hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test',
            'heater_control': heater_switch,
            'target_sensor': ENT_SENSOR,
            'initial_operation_mode': climate.STATE_HEAT
        }})

        self.assertEqual(STATE_OFF,
                         self.hass.states.get(heater_switch).state)

        self._setup_sensor(16)
        self.hass.block_till_done()

        self.assertEqual(STATE_ON,
                         self.hass.states.get(heater_switch).state)

    def test_heater_switch(self):
        """Test heater switching test switch."""
        platform = loader.get_component('switch.test')
        platform.init()
        self.switch_1 = platform.DEVICES[1]
        assert setup_component(self.hass, switch.DOMAIN, {'switch': {
            'platform': 'test'}})
        heater_switch = self.switch_1.entity_id

        assert setup_component(self.hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test',
            'heater_control': heater_switch,
            'target_sensor': ENT_SENSOR,
            'initial_operation_mode': climate.STATE_HEAT
        }})

        self.assertEqual(STATE_OFF,
                         self.hass.states.get(heater_switch).state)

        self._setup_sensor(16)
        self.hass.block_till_done()

        self.assertEqual(STATE_ON,
                         self.hass.states.get(heater_switch).state)

    def _setup_sensor(self, temp, unit=TEMP_CELSIUS):
        """Setup the test sensor."""
        self.hass.states.set(ENT_SENSOR, temp, {
            ATTR_UNIT_OF_MEASUREMENT: unit
        })


class TestClimateGenericThermostatHeat(unittest.TestCase):
    """Test the Generic thermostat in Heat mode."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.units = METRIC_SYSTEM
        assert setup_component(self.hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test',
            'cold_tolerance': 2,
            'hot_tolerance': 4,
            'heater_control': ENT_SWITCH_HEAT,
            'target_sensor': ENT_SENSOR,
            'away_temp_heat': 16
        }})

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_setup_defaults_to_off(self):
        """Test the setting of defaults to STATE_OFF."""
        self.assertEqual(STATE_OFF, self.hass.states.get(ENTITY).state)

    def test_default_setup_params(self):
        """Test the setup with default parameters."""
        state = self.hass.states.get(ENTITY)
        self.assertEqual(DEFAULT_MIN_TEMP, state.attributes.get('min_temp'))
        self.assertEqual(DEFAULT_MAX_TEMP, state.attributes.get('max_temp'))
        self.assertEqual(DEFAULT_TARGET_TEMP_LOW,
                         state.attributes.get(ATTR_TEMPERATURE))

    def test_get_operation_modes(self):
        """Test that the operation list returns the correct modes."""
        state = self.hass.states.get(ENTITY)
        modes = state.attributes.get('operation_list')
        self.assertEqual([STATE_OFF, climate.STATE_HEAT], modes)

    def test_set_target_temp(self):
        """Test the setting of the target temperature."""
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(30.0, state.attributes.get(ATTR_TEMPERATURE))
        climate.set_temperature(self.hass, None)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(30.0, state.attributes.get(ATTR_TEMPERATURE))

    def test_set_operation_mode(self):
        """Test the setting operation mode."""
        climate.set_operation_mode(self.hass, climate.STATE_HEAT)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(climate.STATE_HEAT,
                         state.attributes.get('operation_mode'))
        climate.set_operation_mode(self.hass, climate.STATE_OFF)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(climate.STATE_OFF,
                         state.attributes.get('operation_mode'))
        climate.set_operation_mode(self.hass, climate.STATE_AUTO)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(climate.STATE_OFF,
                         state.attributes.get('operation_mode'))

    def test_set_away_mode_from_off(self):
        """Test the setting away mode."""
        climate.set_temperature(self.hass, 23)
        self.hass.block_till_done()
        climate.set_away_mode(self.hass, True)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(DEFAULT_AWAY_TEMP_HEAT,
                         state.attributes.get('temperature'))
        self.assertEqual(STATE_ON,
                         state.attributes.get('away_mode'))

    def test_set_away_mode_from_heat(self):
        """Test the setting away mode."""
        climate.set_operation_mode(self.hass, climate.STATE_HEAT)
        climate.set_temperature(self.hass, 23)
        self.hass.block_till_done()
        climate.set_away_mode(self.hass, True)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(DEFAULT_AWAY_TEMP_HEAT,
                         state.attributes.get('temperature'))
        self.assertEqual(STATE_ON,
                         state.attributes.get('away_mode'))

    def test_set_away_mode_and_restore_prev_temp(self):
        """Test the setting and removing away mode.

        Verify original temperature is restored.
        """
        climate.set_temperature(self.hass, 23)
        self.hass.block_till_done()
        climate.set_away_mode(self.hass, True)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(DEFAULT_AWAY_TEMP_HEAT,
                         state.attributes.get('temperature'))
        climate.set_away_mode(self.hass, False)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(23, state.attributes.get('temperature'))

    def test_sensor_bad_unit(self):
        """Test sensor that have bad unit."""
        climate.set_temperature(self.hass, 19)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)

        temp = state.attributes.get('current_temperature')
        unit = state.attributes.get('unit_of_measurement')

        self._setup_sensor(22.0, unit='bad_unit')
        self.hass.block_till_done()

        state = self.hass.states.get(ENTITY)
        self.assertEqual(unit, state.attributes.get('unit_of_measurement'))
        self.assertEqual(temp, state.attributes.get('current_temperature'))

    def test_sensor_bad_value(self):
        """Test sensor that have None as state."""
        state = self.hass.states.get(ENTITY)
        temp = state.attributes.get('current_temperature')
        unit = state.attributes.get('unit_of_measurement')

        self._setup_sensor(None)
        self.hass.block_till_done()

        state = self.hass.states.get(ENTITY)
        self.assertEqual(unit, state.attributes.get('unit_of_measurement'))
        self.assertEqual(temp, state.attributes.get('current_temperature'))

    def test_set_target_temp_heater_on(self):
        """Test if target temperature turn heater on."""
        climate.set_operation_mode(self.hass, climate.STATE_HEAT)
        climate.set_temperature(self.hass, 18)
        self._setup_switch(False)
        self._setup_sensor(25)
        self.hass.block_till_done()
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def test_set_target_temp_heater_off(self):
        """Test if target temperature turn heater off."""
        climate.set_operation_mode(self.hass, climate.STATE_HEAT)
        self._setup_switch(True)
        climate.set_temperature(self.hass, 35)
        self._setup_sensor(30)
        self.hass.block_till_done()
        climate.set_temperature(self.hass, 25)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def test_temp_change_heater_on_within_tolerance(self):
        """Test if temperature change doesn't turn on within tolerance."""
        self._setup_switch(False)
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        self._setup_sensor(29)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_temp_change_heater_on_outside_tolerance(self):
        """Test if temperature change turn heater on outside cold tolerance."""
        self._setup_switch(False)
        climate.set_temperature(self.hass, 30)
        climate.set_operation_mode(self.hass, climate.STATE_HEAT)
        self.hass.block_till_done()
        self._setup_sensor(27)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def test_temp_change_heater_off_within_tolerance(self):
        """Test if temperature change doesn't turn off within tolerance."""
        self._setup_switch(True)
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        self._setup_sensor(33)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_temp_change_heater_off_outside_tolerance(self):
        """Test if temperature change turn heater off outside hot tolerance."""
        self._setup_switch(True)
        climate.set_temperature(self.hass, 30)
        climate.set_operation_mode(self.hass, climate.STATE_HEAT)
        self.hass.block_till_done()
        self._setup_sensor(35)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def test_running_when_operating_mode_is_off(self):
        """Test that the switch turns off when enabled is set False."""
        climate.set_operation_mode(self.hass, climate.STATE_HEAT)
        self._setup_switch(True)
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        climate.set_operation_mode(self.hass, STATE_OFF)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def test_no_state_change_when_operation_mode_off(self):
        """Test that the switch doesn't turn on when enabled is False."""
        self._setup_switch(False)
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        climate.set_operation_mode(self.hass, STATE_OFF)
        self.hass.block_till_done()
        self._setup_sensor(25)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))

    @mock.patch('logging.Logger.error')
    def test_invalid_operating_mode(self, log_mock):
        """Test error handling for invalid operation mode."""
        climate.set_operation_mode(self.hass, 'invalid mode')
        self.hass.block_till_done()
        self.assertEqual(log_mock.call_count, 1)

    def test_operating_mode_heat(self):
        """Test change mode from OFF to HEAT.

        Switch turns on when temp below setpoint and mode changes.
        """
        climate.set_operation_mode(self.hass, STATE_OFF)
        climate.set_temperature(self.hass, 30)
        self._setup_sensor(25)
        self.hass.block_till_done()
        self._setup_switch(False)
        climate.set_operation_mode(self.hass, climate.STATE_HEAT)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def _setup_sensor(self, temp, unit=TEMP_CELSIUS):
        """Setup the test sensor."""
        self.hass.states.set(ENT_SENSOR, temp, {
            ATTR_UNIT_OF_MEASUREMENT: unit
        })

    def _setup_switch(self, is_on):
        """Setup the test switch."""
        self.hass.states.set(ENT_SWITCH_HEAT, STATE_ON if is_on else STATE_OFF)
        self.calls = []

        @callback
        def log_call(call):
            """Log service calls."""
            self.calls.append(call)

        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)


class TestClimateGenericThermostatACMode(unittest.TestCase):
    """Test the Generic thermostat."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.temperature_unit = TEMP_CELSIUS
        assert setup_component(self.hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test',
            'cold_tolerance': 2,
            'hot_tolerance': 4,
            'away_temp_cool': DEFAULT_AWAY_TEMP_COOL,
            'ac_control': ENT_SWITCH_AC,
            'target_sensor': ENT_SENSOR,
            'initial_operation_mode': climate.STATE_COOL
        }})

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_set_target_temp_ac_off(self):
        """Test if target temperature turn ac off."""
        self._setup_switch(True)
        self._setup_sensor(25)
        self.hass.block_till_done()
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    def test_turn_away_mode_on_cooling_from_cool(self):
        """Test the setting away mode when cooling."""
        self._setup_sensor(25)
        self.hass.block_till_done()
        climate.set_temperature(self.hass, 19)
        self.hass.block_till_done()
        climate.set_away_mode(self.hass, True)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(DEFAULT_AWAY_TEMP_COOL,
                         state.attributes.get(ATTR_TEMPERATURE))

    def test_turn_away_mode_on_cooling_from_off(self):
        """Test the setting away mode when cooling."""
        self._setup_sensor(25)
        climate.set_operation_mode(self.hass, climate.STATE_OFF)
        self.hass.block_till_done()
        climate.set_temperature(self.hass, 19)
        self.hass.block_till_done()
        climate.set_away_mode(self.hass, True)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(DEFAULT_AWAY_TEMP_COOL,
                         state.attributes.get(ATTR_TEMPERATURE))

    def test_operating_mode_cool(self):
        """Test change mode from OFF to COOL.

        Switch turns on when temp below setpoint and mode changes.
        """
        climate.set_operation_mode(self.hass, STATE_OFF)
        climate.set_temperature(self.hass, 25)
        self._setup_sensor(30)
        self.hass.block_till_done()
        self._setup_switch(False)
        climate.set_operation_mode(self.hass, climate.STATE_COOL)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    def test_set_target_temp_ac_on(self):
        """Test if target temperature turn ac on."""
        self._setup_switch(False)
        climate.set_temperature(self.hass, 31)
        self._setup_sensor(30)
        self.hass.block_till_done()
        climate.set_temperature(self.hass, 25)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    def test_temp_change_ac_off_within_tolerance(self):
        """Test if temperature change doesn't turn ac off within tolerance."""
        self._setup_switch(True)
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        self._setup_sensor(29.8)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_set_temp_change_ac_off_outside_tolerance(self):
        """Test if temperature change turn ac off."""
        self._setup_switch(True)
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        self._setup_sensor(27)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    def test_temp_change_ac_on_within_tolerance(self):
        """Test if temperature change doesn't turn ac on within tolerance."""
        self._setup_switch(False)
        climate.set_temperature(self.hass, 25)
        self.hass.block_till_done()
        self._setup_sensor(25.2)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_temp_change_ac_on_outside_tolerance(self):
        """Test if temperature change turn ac on."""
        self._setup_switch(False)
        climate.set_operation_mode(self.hass, climate.STATE_COOL)
        climate.set_temperature(self.hass, 25)
        self.hass.block_till_done()
        self._setup_sensor(30)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    def test_running_when_operating_mode_is_off(self):
        """Test that the switch turns off when enabled is set False."""
        self._setup_switch(True)
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        climate.set_operation_mode(self.hass, STATE_OFF)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    def test_no_state_change_when_operation_mode_off(self):
        """Test that the switch doesn't turn on when enabled is False."""
        self._setup_switch(False)
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        climate.set_operation_mode(self.hass, STATE_OFF)
        self.hass.block_till_done()
        self._setup_sensor(35)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))

    def _setup_sensor(self, temp, unit=TEMP_CELSIUS):
        """Setup the test sensor."""
        self.hass.states.set(ENT_SENSOR, temp, {
            ATTR_UNIT_OF_MEASUREMENT: unit
        })

    def _setup_switch(self, is_on):
        """Setup the test switch."""
        self.hass.states.set(ENT_SWITCH_AC, STATE_ON if is_on else STATE_OFF)
        self.calls = []

        @callback
        def log_call(call):
            """Log service calls."""
            self.calls.append(call)

        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)


class TestClimateGenericThermostatACModeMinCycle(unittest.TestCase):
    """Test the Generic Thermostat."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.temperature_unit = TEMP_CELSIUS
        assert setup_component(self.hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test',
            'cold_tolerance': 0.3,
            'hot_tolerance': 0.3,
            'ac_control': ENT_SWITCH_AC,
            'target_sensor': ENT_SENSOR,
            'min_cycle_duration': datetime.timedelta(minutes=10),
            'initial_operation_mode': climate.STATE_COOL
        }})

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_temp_change_ac_trigger_on_not_long_enough(self):
        """Test if temperature change turn ac on."""
        self._setup_switch(False)
        climate.set_temperature(self.hass, 25)
        self.hass.block_till_done()
        self._setup_sensor(30)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_temp_change_ac_trigger_on_long_enough(self):
        """Test if temperature change turn ac on."""
        fake_changed = datetime.datetime(1918, 11, 11, 11, 11, 11,
                                         tzinfo=datetime.timezone.utc)
        with mock.patch('homeassistant.helpers.condition.dt_util.utcnow',
                        return_value=fake_changed):
            self._setup_switch(False)
        climate.set_temperature(self.hass, 25)
        self.hass.block_till_done()
        self._setup_sensor(30)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    def test_temp_change_ac_trigger_off_not_long_enough(self):
        """Test if temperature change turn ac on."""
        self._setup_switch(True)
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        self._setup_sensor(25)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_temp_change_ac_trigger_off_long_enough(self):
        """Test if temperature change turn ac on."""
        fake_changed = datetime.datetime(1918, 11, 11, 11, 11, 11,
                                         tzinfo=datetime.timezone.utc)
        with mock.patch('homeassistant.helpers.condition.dt_util.utcnow',
                        return_value=fake_changed):
            self._setup_switch(True)
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        self._setup_sensor(25)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    def _setup_sensor(self, temp, unit=TEMP_CELSIUS):
        """Setup the test sensor."""
        self.hass.states.set(ENT_SENSOR, temp, {
            ATTR_UNIT_OF_MEASUREMENT: unit
        })

    def _setup_switch(self, is_on):
        """Setup the test switch."""
        self.hass.states.set(ENT_SWITCH_AC, STATE_ON if is_on else STATE_OFF)
        self.calls = []

        @callback
        def log_call(call):
            """Log service calls."""
            self.calls.append(call)

        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)


class TestClimateGenericThermostatMinCycle(unittest.TestCase):
    """Test the Generic thermostat."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.temperature_unit = TEMP_CELSIUS
        assert setup_component(self.hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test',
            'cold_tolerance': 0.3,
            'hot_tolerance': 0.3,
            'heater_control': ENT_SWITCH_HEAT,
            'target_sensor': ENT_SENSOR,
            'min_cycle_duration': datetime.timedelta(minutes=10),
            'initial_operation_mode': climate.STATE_HEAT
        }})

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_temp_change_heater_trigger_off_not_long_enough(self):
        """Test if temp change doesn't turn heater off because of time."""
        self._setup_switch(True)
        climate.set_temperature(self.hass, 25)
        self.hass.block_till_done()
        self._setup_sensor(30)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_temp_change_heater_trigger_on_not_long_enough(self):
        """Test if temp change doesn't turn heater on because of time."""
        self._setup_switch(False)
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        self._setup_sensor(25)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_temp_change_heater_trigger_on_long_enough(self):
        """Test if temperature change turn heater on after min cycle."""
        fake_changed = datetime.datetime(1918, 11, 11, 11, 11, 11,
                                         tzinfo=datetime.timezone.utc)
        with mock.patch('homeassistant.helpers.condition.dt_util.utcnow',
                        return_value=fake_changed):
            self._setup_switch(False)
        self.hass.block_till_done()
        climate.set_temperature(self.hass, 30)
        self.hass.block_till_done()
        self._setup_sensor(25)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def test_temp_change_heater_trigger_off_long_enough(self):
        """Test if temperature change turn heater off after min cycle."""
        fake_changed = datetime.datetime(1918, 11, 11, 11, 11, 11,
                                         tzinfo=datetime.timezone.utc)
        with mock.patch('homeassistant.helpers.condition.dt_util.utcnow',
                        return_value=fake_changed):
            self._setup_switch(True)
        climate.set_temperature(self.hass, 25)
        self.hass.block_till_done()
        self._setup_sensor(30)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def _setup_sensor(self, temp, unit=TEMP_CELSIUS):
        """Setup the test sensor."""
        self.hass.states.set(ENT_SENSOR, temp, {
            ATTR_UNIT_OF_MEASUREMENT: unit
        })

    def _setup_switch(self, is_on):
        """Setup the test switch."""
        self.hass.states.set(ENT_SWITCH_HEAT, STATE_ON if is_on else STATE_OFF)
        self.calls = []

        @callback
        def log_call(call):
            """Log service calls."""
            self.calls.append(call)

        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)


class TestClimateGenericThermostatACKeepAlive(unittest.TestCase):
    """Test the Generic Thermostat."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.temperature_unit = TEMP_CELSIUS
        assert setup_component(self.hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test',
            'cold_tolerance': 0.3,
            'hot_tolerance': 0.3,
            'ac_control': ENT_SWITCH_AC,
            'target_sensor': ENT_SENSOR,
            'ac_mode': True,
            'keep_alive': datetime.timedelta(minutes=10)
        }})

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_temp_change_ac_trigger_on_long_enough(self):
        """Test if turn on signal is sent at keep-alive intervals."""
        self._setup_switch(True)
        self.hass.block_till_done()
        self._setup_sensor(30)
        self.hass.block_till_done()
        climate.set_temperature(self.hass, 25)
        self.hass.block_till_done()
        test_time = datetime.datetime.now(pytz.UTC)
        self._send_time_changed(test_time)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))
        self._send_time_changed(test_time + datetime.timedelta(minutes=5))
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))
        self._send_time_changed(test_time + datetime.timedelta(minutes=10))
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    def test_temp_change_ac_trigger_off_long_enough(self):
        """Test if turn on signal is sent at keep-alive intervals."""
        self._setup_switch(False)
        self.hass.block_till_done()
        self._setup_sensor(20)
        self.hass.block_till_done()
        climate.set_temperature(self.hass, 25)
        self.hass.block_till_done()
        test_time = datetime.datetime.now(pytz.UTC)
        self._send_time_changed(test_time)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))
        self._send_time_changed(test_time + datetime.timedelta(minutes=5))
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))
        self._send_time_changed(test_time + datetime.timedelta(minutes=10))
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    def _send_time_changed(self, now):
        """Send a time changed event."""
        self.hass.bus.fire(ha.EVENT_TIME_CHANGED, {ha.ATTR_NOW: now})

    def _setup_sensor(self, temp, unit=TEMP_CELSIUS):
        """Setup the test sensor."""
        self.hass.states.set(ENT_SENSOR, temp, {
            ATTR_UNIT_OF_MEASUREMENT: unit
        })

    def _setup_switch(self, is_on):
        """Setup the test switch."""
        self.hass.states.set(ENT_SWITCH_AC, STATE_ON if is_on else STATE_OFF)
        self.calls = []

        @callback
        def log_call(call):
            """Log service calls."""
            self.calls.append(call)

        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)


class TestClimateGenericThermostatKeepAlive(unittest.TestCase):
    """Test the Generic Thermostat."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.temperature_unit = TEMP_CELSIUS
        assert setup_component(self.hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test',
            'cold_tolerance': 0.3,
            'hot_tolerance': 0.3,
            'heater_control': ENT_SWITCH_HEAT,
            'target_sensor': ENT_SENSOR,
            'keep_alive': datetime.timedelta(minutes=10)
        }})

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_temp_change_heater_trigger_on_long_enough(self):
        """Test if turn on signal is sent at keep-alive intervals."""
        self._setup_switch(True)
        self.hass.block_till_done()
        self._setup_sensor(20)
        self.hass.block_till_done()
        climate.set_temperature(self.hass, 25)
        self.hass.block_till_done()
        test_time = datetime.datetime.now(pytz.UTC)
        self._send_time_changed(test_time)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))
        self._send_time_changed(test_time + datetime.timedelta(minutes=5))
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))
        self._send_time_changed(test_time + datetime.timedelta(minutes=10))
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def test_temp_change_heater_trigger_off_long_enough(self):
        """Test if turn on signal is sent at keep-alive intervals."""
        self._setup_switch(False)
        self.hass.block_till_done()
        self._setup_sensor(30)
        self.hass.block_till_done()
        climate.set_temperature(self.hass, 25)
        self.hass.block_till_done()
        test_time = datetime.datetime.now(pytz.UTC)
        self._send_time_changed(test_time)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))
        self._send_time_changed(test_time + datetime.timedelta(minutes=5))
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))
        self._send_time_changed(test_time + datetime.timedelta(minutes=10))
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def _send_time_changed(self, now):
        """Send a time changed event."""
        self.hass.bus.fire(ha.EVENT_TIME_CHANGED, {ha.ATTR_NOW: now})

    def _setup_sensor(self, temp, unit=TEMP_CELSIUS):
        """Setup the test sensor."""
        self.hass.states.set(ENT_SENSOR, temp, {
            ATTR_UNIT_OF_MEASUREMENT: unit
        })

    def _setup_switch(self, is_on):
        """Setup the test switch."""
        self.hass.states.set(ENT_SWITCH_HEAT, STATE_ON if is_on else STATE_OFF)
        self.calls = []

        @callback
        def log_call(call):
            """Log service calls."""
            self.calls.append(call)

        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)


class TestClimateGenericThermostatDualSwitchMinCycle(unittest.TestCase):
    """Test the Generic thermostat."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.temperature_unit = TEMP_CELSIUS
        assert setup_component(self.hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test',
            'heater_control': ENT_SWITCH_HEAT,
            'ac_control': ENT_SWITCH_AC,
            'target_sensor': ENT_SENSOR,
            'min_cycle_duration': datetime.timedelta(minutes=10),
            'initial_operation_mode': climate.STATE_AUTO
        }})

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_temp_change_ac_trigger_on_not_long_enough(self):
        """Test if temperature change turn ac on."""
        self._setup_switch_heat(False)
        self._setup_switch_ac(False)
        climate.set_temperature(self.hass, None, None, 25, 20)
        self.hass.block_till_done()
        self._setup_sensor(30)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_temp_change_ac_trigger_on_long_enough(self):
        """Test if temperature change turn ac on."""
        fake_changed = datetime.datetime(1918, 11, 11, 11, 11, 11,
                                         tzinfo=datetime.timezone.utc)
        with mock.patch('homeassistant.helpers.condition.dt_util.utcnow',
                        return_value=fake_changed):
            self._setup_switch_heat(False)
            self._setup_switch_ac(False)
        climate.set_operation_mode(self.hass, climate.STATE_COOL)
        climate.set_temperature(self.hass, None, None, 25, 20)
        self.hass.block_till_done()
        self._setup_sensor(30)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    def test_temp_change_heat_trigger_on_long_enough(self):
        """Test if temperature change turn ac on."""
        fake_changed = datetime.datetime(1918, 11, 11, 11, 11, 11,
                                         tzinfo=datetime.timezone.utc)
        with mock.patch('homeassistant.helpers.condition.dt_util.utcnow',
                        return_value=fake_changed):
            self._setup_switch_heat(False)
            self._setup_switch_ac(False)
        climate.set_operation_mode(self.hass, climate.STATE_HEAT)
        climate.set_temperature(self.hass, None, None, 25, 20)
        self.hass.block_till_done()
        self._setup_sensor(17)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def _setup_sensor(self, temp, unit=TEMP_CELSIUS):
        """Setup the test sensor."""
        self.hass.states.set(ENT_SENSOR, temp, {
            ATTR_UNIT_OF_MEASUREMENT: unit
        })

    def _setup_switch_heat(self, is_on):
        """Setup the test heating switch."""
        self.hass.states.set(ENT_SWITCH_HEAT, STATE_ON if is_on else STATE_OFF)
        self.calls = []

        @callback
        def log_call(call):
            """Log service calls."""
            self.calls.append(call)

        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)

    def _setup_switch_ac(self, is_on):
        """Setup the test A/C switch."""
        self.hass.states.set(ENT_SWITCH_AC, STATE_ON if is_on else STATE_OFF)
        self.calls = []

        @callback
        def log_call(call):
            """Log service calls."""
            self.calls.append(call)

        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)


class TestClimateGenericThermostatDualSwitch(unittest.TestCase):
    """Test the Generic thermostat."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.temperature_unit = TEMP_CELSIUS
        assert setup_component(self.hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test',
            'heater_control': ENT_SWITCH_HEAT,
            'ac_control': ENT_SWITCH_AC,
            'away_temp_cool': DEFAULT_AWAY_TEMP_COOL,
            'away_temp_heat': DEFAULT_AWAY_TEMP_HEAT,
            'target_sensor': ENT_SENSOR,
            'initial_operation_mode': climate.STATE_AUTO
        }})

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_setup_defaults_to_initial_state(self):
        """Test the setting of defaults to STATE_AUTO."""
        self.assertEqual(climate.STATE_AUTO,
                         self.hass.states.get(ENTITY).
                         attributes.get('operation_mode'))

    def test_default_setup_params(self):
        """Test the setup with default parameters."""
        state = self.hass.states.get(ENTITY)
        self.assertEqual(DEFAULT_TARGET_TEMP_HIGH,
                         state.attributes.get('target_temp_high'))
        self.assertEqual(DEFAULT_TARGET_TEMP_LOW,
                         state.attributes.get('target_temp_low'))
        self.assertEqual(None,
                         state.attributes.get(ATTR_TEMPERATURE))

    def test_set_operation_mode(self):
        """Test the setting operation mode."""
        climate.set_operation_mode(self.hass, climate.STATE_HEAT)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(climate.STATE_HEAT,
                         state.attributes.get('operation_mode'))
        climate.set_operation_mode(self.hass, climate.STATE_OFF)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(climate.STATE_OFF,
                         state.attributes.get('operation_mode'))
        climate.set_operation_mode(self.hass, climate.STATE_AUTO)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(climate.STATE_AUTO,
                         state.attributes.get('operation_mode'))
        climate.set_operation_mode(self.hass, 'invalid mode')
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(climate.STATE_AUTO,
                         state.attributes.get('operation_mode'))

    def test_set_away_mode_and_restore_prev_temp(self):
        """Test the setting and removing away mode.

        Verify original temperature is restored.
        """
        climate.set_temperature(self.hass, None, None, 22, 20)
        self.hass.block_till_done()
        climate.set_away_mode(self.hass, True)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(DEFAULT_AWAY_TEMP_COOL,
                         state.attributes.get('target_temp_high'))
        self.assertEqual(DEFAULT_AWAY_TEMP_HEAT,
                         state.attributes.get('target_temp_low'))
        climate.set_away_mode(self.hass, False)
        self.hass.block_till_done()
        state = self.hass.states.get(ENTITY)
        self.assertEqual(22, state.attributes.get('target_temp_high'))
        self.assertEqual(20, state.attributes.get('target_temp_low'))

    def test_set_target_temp_heater_off(self):
        """Test if target temperature turn heater off."""
        self._setup_switch_heat(True)
        climate.set_temperature(self.hass, None, None, 25, 20)
        self._setup_sensor(19)
        self.hass.block_till_done()
        climate.set_temperature(self.hass, None, None, 25, 18)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def test_sensor_move_inside_heater_interval(self):
        """Test complete intervals.

        Verify all positions of sensor temperature.
        Observe correct service calls.
        """
        self._setup_sensor(19)
        self._setup_switch_heat(False)
        self._setup_switch_ac(False)
        self.hass.block_till_done()
        self._setup_sensor(17.9)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))
        self._setup_sensor(17)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def test_sensor_move_outside_heater(self):
        """Test complete intervals.

        Verify all positions of sensor temperature.
        Observe correct service calls.
        """
        self._setup_sensor(17)
        self._setup_switch_heat(True)
        self._setup_switch_ac(False)
        self.hass.block_till_done()
        self._setup_sensor(18.2)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))
        self._setup_sensor(19)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_HEAT, call.data['entity_id'])

    def test_sensor_move_inside_ac_interval(self):
        """Test complete intervals.

        Verify all positions of sensor temperature.
        Observe correct service calls.
        """
        self._setup_sensor(19)
        self._setup_switch_heat(False)
        self._setup_switch_ac(False)
        self.hass.block_till_done()
        self._setup_sensor(21.1)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))
        self._setup_sensor(22)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_ON, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    @mock.patch('logging.Logger.error')
    def test_invalid_both_heating_and_cooling_on(self, log_mock):
        """Test error handling for state of heat and cool."""
        self._setup_switch_heat(True)
        self._setup_switch_ac(False)
        self.hass.block_till_done()
        self._setup_switch_ac(True)
        self.hass.block_till_done()
        self.assertEqual(log_mock.call_count, 1)
        self.assertEqual(2, len(self.calls))
        call1 = self.calls[0]
        self.assertEqual('homeassistant', call1.domain)
        self.assertEqual(SERVICE_TURN_OFF, call1.service)
        self.assertEqual(ENT_SWITCH_HEAT, call1.data['entity_id'])
        call2 = self.calls[1]
        self.assertEqual('homeassistant', call2.domain)
        self.assertEqual(SERVICE_TURN_OFF, call2.service)
        self.assertEqual(ENT_SWITCH_AC, call2.data['entity_id'])

    def test_sensor_move_outside_ac(self):
        """Test complete intervals.

        Verify all positions of sensor temperature.
        Observe correct service calls.
        """
        self._setup_sensor(22)
        self._setup_switch_heat(False)
        self._setup_switch_ac(True)
        self.hass.block_till_done()
        self._setup_sensor(20.9)
        self.hass.block_till_done()
        self.assertEqual(0, len(self.calls))
        self._setup_sensor(19)
        self.hass.block_till_done()
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual('homeassistant', call.domain)
        self.assertEqual(SERVICE_TURN_OFF, call.service)
        self.assertEqual(ENT_SWITCH_AC, call.data['entity_id'])

    def _setup_sensor(self, temp, unit=TEMP_CELSIUS):
        """Setup the test sensor."""
        self.hass.states.set(ENT_SENSOR, temp, {
            ATTR_UNIT_OF_MEASUREMENT: unit
        })

    def _setup_switch_heat(self, is_on):
        """Setup the test heating switch."""
        self.hass.states.set(ENT_SWITCH_HEAT, STATE_ON if is_on else STATE_OFF)
        self.calls = []

        @callback
        def log_call(call):
            """Log service calls."""
            self.calls.append(call)

        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)

    def _setup_switch_ac(self, is_on):
        """Setup the test A/C switch."""
        self.hass.states.set(ENT_SWITCH_AC, STATE_ON if is_on else STATE_OFF)
        self.calls = []

        @callback
        def log_call(call):
            """Log service calls."""
            self.calls.append(call)

        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
        self.hass.services.register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)


@asyncio.coroutine
def test_custom_setup_params(hass):
    """Test the setup with custom parameters."""
    result = yield from async_setup_component(
        hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test',
            'heater_control': ENT_SWITCH_HEAT,
            'target_sensor': ENT_SENSOR,
            'min_temp': MIN_TEMP,
            'max_temp': MAX_TEMP,
            'target_temp': TARGET_TEMP
        }})
    assert result
    state = hass.states.get(ENTITY)
    assert state.attributes.get('min_temp') == MIN_TEMP
    assert state.attributes.get('max_temp') == MAX_TEMP
    assert state.attributes.get(ATTR_TEMPERATURE) == TARGET_TEMP


@asyncio.coroutine
def test_restore_state(hass):
    """Ensure states are restored on startup."""
    mock_restore_cache(hass, (
        State('climate.test_thermostat', '0', {ATTR_TEMPERATURE: "20",
              climate.ATTR_OPERATION_MODE: "off", ATTR_AWAY_MODE: "on",
              climate.ATTR_TARGET_TEMP_LOW: "17",
              climate.ATTR_TARGET_TEMP_HIGH: "23"}),
    ))

    hass.state = CoreState.starting

    yield from async_setup_component(
        hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test_thermostat',
            'heater_control': ENT_SWITCH_HEAT,
            'target_sensor': ENT_SENSOR,
        }})

    state = hass.states.get('climate.test_thermostat')
    assert(state.attributes[ATTR_TEMPERATURE] == 20)
    assert(state.attributes[climate.ATTR_OPERATION_MODE] == "off")
    assert(state.state == STATE_OFF)


@asyncio.coroutine
def test_restore_dual_temp(hass):
    """Ensure states are restored on startup."""
    mock_restore_cache(hass, (
        State('climate.test_thermostat', '0', {
              climate.ATTR_OPERATION_MODE: "off",
              ATTR_AWAY_MODE: "on",
              climate.ATTR_TARGET_TEMP_LOW: "17",
              climate.ATTR_TARGET_TEMP_HIGH: "23"}),
    ))

    hass.state = CoreState.starting

    yield from async_setup_component(
        hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test_thermostat',
            'heater_control': ENT_SWITCH_HEAT,
            'ac_control': ENT_SWITCH_AC,
            'target_sensor': ENT_SENSOR,
        }})

    state = hass.states.get('climate.test_thermostat')
    assert(state.attributes[climate.ATTR_TARGET_TEMP_LOW] == 17)
    assert(state.attributes[climate.ATTR_TARGET_TEMP_HIGH] == 23)


@asyncio.coroutine
def test_no_restore_state(hass):
    """Ensure states are restored on startup if they exist.

    Allows for graceful reboot.
    """
    mock_restore_cache(hass, (
        State('climate.test_thermostat', '0', {ATTR_TEMPERATURE: "20",
              climate.ATTR_OPERATION_MODE: "cool", ATTR_AWAY_MODE: "on"}),
    ))

    hass.state = CoreState.starting

    yield from async_setup_component(
        hass, climate.DOMAIN, {'climate': {
            'platform': 'generic_thermostat',
            'name': 'test_thermostat',
            'heater_control': ENT_SWITCH_HEAT,
            'target_sensor': ENT_SENSOR,
            'target_temp': 22
        }})

    state = hass.states.get('climate.test_thermostat')
    assert(state.attributes[ATTR_TEMPERATURE] == 22)
    assert(state.attributes[climate.ATTR_OPERATION_MODE] == "off")
