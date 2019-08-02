"""Tests for the vaillant sensor."""
import datetime

import pytest
from vr900connector.model import System, HeatingMode, QuickMode, HolidayMode, \
    HotWater, Room, Zone

from homeassistant.components.climate.const import PRESET_COMFORT, \
    HVAC_MODE_AUTO, HVAC_MODE_OFF, PRESET_AWAY, HVAC_MODE_HEAT
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
import homeassistant.components.vaillant as vaillant
from homeassistant.components.vaillant import DOMAIN, CONF_ROOM_CLIMATE, \
    CONF_ZONE_CLIMATE
from tests.components.vaillant import SystemManagerMock, _goto_future, _setup

VALID_ALL_DISABLED_CONFIG = {
    DOMAIN: {
        CONF_USERNAME: 'test',
        CONF_PASSWORD: 'test',
        CONF_ROOM_CLIMATE: False,
        CONF_ZONE_CLIMATE: False
    }
}


def _assert_room_state(hass, hvac, preset, temp, current_temp):
    """Assert room climate state."""
    state = hass.states.get('climate.vaillant_room_1')

    assert hass.states.is_state('climate.vaillant_room_1', hvac)
    assert state.attributes['current_temperature'] == current_temp
    assert state.attributes['preset_mode'] == preset
    assert state.attributes['max_temp'] == Room.MAX_TEMP
    assert state.attributes['min_temp'] == Room.MIN_TEMP
    assert state.attributes['temperature'] == temp
    assert set(state.attributes['hvac_modes']) == {'off', 'heat', 'auto'}
    assert set(state.attributes['preset_modes']) == \
        {'home', 'away', 'boost', 'comfort'}


def _assert_zone_state(hass, hvac, preset, target_high, target_low, current_temp):
    """Assert zone climate state."""
    state = hass.states.get('climate.vaillant_zone_1')

    assert hass.states.is_state('climate.vaillant_zone_1', hvac)
    assert state.attributes['current_temperature'] == current_temp
    assert state.attributes['preset_mode'] == preset
    assert state.attributes['max_temp'] == Zone.MAX_TEMP
    assert state.attributes['min_temp'] == Zone.MIN_TEMP
    assert state.attributes['target_temp_high'] == target_high
    assert state.attributes['target_temp_low'] == target_low
    assert set(state.attributes['hvac_modes']) == \
        {'off', 'auto', 'heat', 'cool', 'fan_only'}
    assert set(state.attributes['preset_modes']) == \
        {'boost', 'comfort', 'away', 'sleep', 'home'}


@pytest.fixture(autouse=True)
def fixture_only_climate(mock_system_manager):
    """Mock vaillant to only handle sensor."""
    orig_platforms = vaillant.PLATFORMS
    vaillant.PLATFORMS = ['climate']
    yield
    vaillant.PLATFORMS = orig_platforms


async def test_valid_config(hass):
    """Test setup with valid config."""
    assert await _setup(hass)
    assert len(hass.states.async_entity_ids()) == 2
    _assert_room_state(hass, HVAC_MODE_AUTO, PRESET_COMFORT, 20, 22)
    _assert_zone_state(hass, HVAC_MODE_AUTO, PRESET_COMFORT, 30, 22, 25)


async def test_valid_config_all_disabled(hass):
    """Test setup with valid config, but water heater disabled."""
    assert await _setup(hass, VALID_ALL_DISABLED_CONFIG)
    assert not hass.states.async_entity_ids()


async def test_empty_system(hass):
    """Test setup with empty system."""
    assert await _setup(hass, system=System(None, None, None, None,
                                            None, None, None, None,
                                            None))
    assert not hass.states.async_entity_ids()


async def test_state_update_room(hass):
    """Test room climate is updated accordingly to data."""
    assert await _setup(hass)
    _assert_room_state(hass, HVAC_MODE_AUTO, PRESET_COMFORT, 20, 22)

    system = SystemManagerMock.system
    system.get_room(1).current_temperature = 25
    system.get_room(1).target_temperature = 30
    system.get_room(1).time_program = \
        SystemManagerMock.time_program(HeatingMode.ON, 30)
    await _goto_future(hass)

    _assert_room_state(hass, HVAC_MODE_AUTO, PRESET_COMFORT, 30, 25)


async def test_room_heating_off(hass):
    """Test water heater is updated accordingly to data."""
    system = SystemManagerMock.get_default_system()
    system.get_room(1).operation_mode = HeatingMode.OFF

    assert await _setup(hass, system=system)
    _assert_room_state(hass, HVAC_MODE_OFF, PRESET_AWAY, Room.MIN_TEMP, 22)


async def test_room_heating_manual(hass):
    """Test water heater is updated accordingly to data."""
    system = SystemManagerMock.get_default_system()
    system.get_room(1).operation_mode = HeatingMode.MANUAL

    assert await _setup(hass, system=system)
    _assert_room_state(hass, HVAC_MODE_HEAT, PRESET_COMFORT, 24, 22)


async def test_holiday_mode(hass):
    """Test holiday mode."""
    system = SystemManagerMock.get_default_system()
    system.quick_mode = QuickMode.QM_HOLIDAY
    system.holiday_mode = HolidayMode(True, datetime.date.today(),
                                      datetime.date.today(), 15)

    assert await _setup(hass, system=system)
    _assert_room_state(hass, HVAC_MODE_OFF, PRESET_AWAY, 15, 22)

    #
    #
    # async def test_holiday_mode(hass):
    #     """Test holiday mode."""
    #     system = SystemManagerMock.get_default_system()
    #     system.quick_mode = QuickMode.QM_HOLIDAY
    #     system.holiday_mode = HolidayMode(True, datetime.date.today(),
    #                                       datetime.date.today(), 15)
    #
    #     assert await _setup(hass, system=system)
    #     _assert_state(hass, QuickMode.QM_HOLIDAY, HotWater.MIN_TEMP, 45, 'on')
    #
    #
    # async def test_away_mode(hass):
    #     """Test away mode."""
    #     system = SystemManagerMock.get_default_system()
    #     system.hot_water.operation_mode = HeatingMode.OFF
    #
    #     assert await _setup(hass, system=system)
    #     _assert_state(hass, HeatingMode.OFF, HotWater.MIN_TEMP, 45, 'on')
    #
    #
    # async def test_water_boost(hass):
    #     """Test hot water boost mode."""
    #     system = SystemManagerMock.get_default_system()
    #     system.quick_mode = QuickMode.QM_HOTWATER_BOOST
    #
    #     assert await _setup(hass, system=system)
    #     _assert_state(hass, QuickMode.QM_HOTWATER_BOOST, 40,
    #                   45, 'off')
    #
    #
    # async def test_system_off(hass):
    #     """Test system off mode."""
    #     system = SystemManagerMock.get_default_system()
    #     system.quick_mode = QuickMode.QM_SYSTEM_OFF
    #
    #     assert await _setup(hass, system=system)
    #     _assert_state(hass, QuickMode.QM_SYSTEM_OFF, HotWater.MIN_TEMP, 45, 'on')
    #
    #
    # async def test_one_day_away(hass):
    #     """Test one day away mode."""
    #     system = SystemManagerMock.get_default_system()
    #     system.quick_mode = QuickMode.QM_ONE_DAY_AWAY
    #
    #     assert await _setup(hass, system=system)
    #     _assert_state(hass, QuickMode.QM_ONE_DAY_AWAY, HotWater.MIN_TEMP, 45, 'on')
    #
    #
    # async def test_turn_away_mode_on(hass):
    #     """Test turn away mode on."""
    #     assert await _setup(hass)
    #
    #     hot_water = SystemManagerMock.system.hot_water
    #     hot_water.operation_mode = HeatingMode.OFF
    #     SystemManagerMock.instance.get_hot_water.return_value = hot_water
    #
    #     await hass.services.async_call('water_heater',
    #                                    'set_away_mode',
    #                                    {
    #                                        'entity_id':
    #                                            'water_heater.vaillant_hot_water',
    #                                        'away_mode': True
    #                                    })
    #     await hass.async_block_till_done()
    #
    #     SystemManagerMock.instance.set_hot_water_operation_mode.\
    #         assert_called_once_with(ANY, HeatingMode.OFF)
    #     _assert_state(hass, HeatingMode.OFF, HotWater.MIN_TEMP, 45, 'on')
    #
    #
    # async def test_turn_away_mode_off(hass):
    #     """Test turn away mode off."""
    #     assert await _setup(hass)
    #
    #     hot_water = SystemManagerMock.system.hot_water
    #     hot_water.operation_mode = HeatingMode.AUTO
    #     SystemManagerMock.instance.get_hot_water.return_value = hot_water
    #
    #     await hass.services.async_call('water_heater',
    #                                    'set_away_mode',
    #                                    {
    #                                        'entity_id':
    #                                            'water_heater.vaillant_hot_water',
    #                                        'away_mode': False
    #                                    })
    #     await hass.async_block_till_done()
    #
    #     SystemManagerMock.instance.set_hot_water_operation_mode.\
    #         assert_called_once_with(ANY, HeatingMode.AUTO)
    #
    #     _assert_state(hass, HeatingMode.AUTO, HotWater.MIN_TEMP, 45, 'off')
    #
    #
    # async def test_set_operation_mode(hass):
    #     """Test set operation mode."""
    #     assert await _setup(hass)
    #
    #     hot_water = SystemManagerMock.system.hot_water
    #     hot_water.operation_mode = HeatingMode.ON
    #     SystemManagerMock.instance.get_hot_water.return_value = hot_water
    #
    #     await hass.services.async_call('water_heater',
    #                                    'set_operation_mode',
    #                                    {
    #                                        'entity_id':
    #                                            'water_heater.vaillant_hot_water',
    #                                        'operation_mode': 'ON'
    #                                    })
    #     await hass.async_block_till_done()
    #
    #     SystemManagerMock.instance.set_hot_water_operation_mode\
    #         .assert_called_once_with(ANY, HeatingMode.ON)
    #     _assert_state(hass, HeatingMode.ON, 40, 45, 'off')
    #
    #
    # async def test_set_operation_mode_wrong(hass):
    #     """Test set operation mode with wrong mode."""
    #     assert await _setup(hass)
    #
    #     await hass.services.async_call('water_heater',
    #                                    'set_operation_mode',
    #                                    {
    #                                        'entity_id':
    #                                            'water_heater.vaillant_hot_water',
    #                                        'operation_mode': 'wrong'
    #                                    })
    #     await hass.async_block_till_done()
    #
    #     SystemManagerMock.instance.set_hot_water_operation_mode\
    #         .assert_not_called()
    #     _assert_state(hass, HeatingMode.AUTO, HotWater.MIN_TEMP, 45, 'off')
    #
    #
    # async def test_set_temperature(hass):
    #     """Test set target temperature."""
    #     system = SystemManagerMock.get_default_system()
    #     system.hot_water.operation_mode = HeatingMode.ON
    #     assert await _setup(hass, system=system)
    #
    #     SystemManagerMock.system.hot_water.target_temperature = 50
    #     SystemManagerMock.instance.get_hot_water.return_value = \
    #         SystemManagerMock.system.hot_water
    #
    #     await hass.services.async_call('water_heater',
    #                                    'set_temperature',
    #                                    {
    #                                        'entity_id':
    #                                            'water_heater.vaillant_hot_water',
    #                                        'temperature': 50
    #                                    })
    #     await hass.async_block_till_done()
    #
    #     SystemManagerMock.instance.set_hot_water_setpoint_temperature \
    #         .assert_called_once_with(ANY, 50)
    #     _assert_state(hass, HeatingMode.ON, 50, 45, 'off')
