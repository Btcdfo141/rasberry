"""Tests for the vaillant sensor."""
import datetime

import pytest
from mock import ANY
from vr900connector.model import System, HeatingMode, QuickMode, HolidayMode, \
    HotWater

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
import homeassistant.components.vaillant as vaillant
from homeassistant.components.vaillant import DOMAIN, CONF_WATER_HEATER
from tests.components.vaillant import SystemManagerMock, _goto_future, _setup

VALID_ALL_DISABLED_CONFIG = {
    DOMAIN: {
        CONF_USERNAME: 'test',
        CONF_PASSWORD: 'test',
        CONF_WATER_HEATER: False,
    }
}


def _assert_state(hass, mode, temp, current_temp, away_mode):
    assert len(hass.states.async_entity_ids()) == 1

    assert hass.states.is_state('water_heater.vaillant_hot_water', mode.name)
    state = hass.states.get('water_heater.vaillant_hot_water')
    assert state.attributes['min_temp'] == HotWater.MIN_TEMP
    assert state.attributes['max_temp'] == HotWater.MAX_TEMP
    assert state.attributes['temperature'] == temp
    assert state.attributes['current_temperature'] == current_temp
    assert state.attributes['operation_mode'] == mode.name
    assert state.attributes['away_mode'] == away_mode
    assert state.attributes['operation_list'] == \
        ['ON', 'OFF', 'AUTO', 'QM_HOTWATER_BOOST', 'QM_ONE_DAY_AWAY',
         'QM_SYSTEM_OFF']


@pytest.fixture(autouse=True)
def fixture_only_water_heater(mock_system_manager):
    """Mock vaillant to only handle sensor."""
    orig_platforms = vaillant.PLATFORMS
    vaillant.PLATFORMS = ['water_heater']
    yield
    vaillant.PLATFORMS = orig_platforms


async def test_valid_config(hass):
    """Test setup with valid config."""
    assert await _setup(hass)
    _assert_state(hass, HeatingMode.AUTO, HotWater.MIN_TEMP, 45, 'off')


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


async def test_state_update(hass):
    """Test water heater is updated accordingly to data."""
    assert await _setup(hass)
    _assert_state(hass, HeatingMode.AUTO, HotWater.MIN_TEMP, 45, 'off')

    system = SystemManagerMock.system
    system.hot_water.current_temperature = 65
    system.hot_water.operation_mode = HeatingMode.ON
    system.hot_water.target_temperature = 45
    SystemManagerMock.system = system
    await _goto_future(hass)

    _assert_state(hass, HeatingMode.ON, 45, 65, 'off')


async def test_holiday_mode(hass):
    """Test holiday mode."""
    system = SystemManagerMock.get_default_system()
    system.quick_mode = QuickMode.QM_HOLIDAY
    system.holiday_mode = HolidayMode(True, datetime.date.today(),
                                      datetime.date.today(), 15)

    assert await _setup(hass, system=system)
    _assert_state(hass, QuickMode.QM_HOLIDAY, HotWater.MIN_TEMP, 45, 'on')


async def test_away_mode(hass):
    """Test away mode."""
    system = SystemManagerMock.get_default_system()
    system.hot_water.operation_mode = HeatingMode.OFF

    assert await _setup(hass, system=system)
    _assert_state(hass, HeatingMode.OFF, HotWater.MIN_TEMP, 45, 'on')


async def test_water_boost(hass):
    """Test hot water boost mode."""
    system = SystemManagerMock.get_default_system()
    system.quick_mode = QuickMode.QM_HOTWATER_BOOST

    assert await _setup(hass, system=system)
    _assert_state(hass, QuickMode.QM_HOTWATER_BOOST, 40,
                  45, 'off')


async def test_system_off(hass):
    """Test system off mode."""
    system = SystemManagerMock.get_default_system()
    system.quick_mode = QuickMode.QM_SYSTEM_OFF

    assert await _setup(hass, system=system)
    _assert_state(hass, QuickMode.QM_SYSTEM_OFF, HotWater.MIN_TEMP, 45, 'on')


async def test_one_day_away(hass):
    """Test one day away mode."""
    system = SystemManagerMock.get_default_system()
    system.quick_mode = QuickMode.QM_ONE_DAY_AWAY

    assert await _setup(hass, system=system)
    _assert_state(hass, QuickMode.QM_ONE_DAY_AWAY, HotWater.MIN_TEMP, 45, 'on')


async def test_turn_away_mode_on(hass):
    """Test turn away mode on."""
    assert await _setup(hass)

    hot_water = SystemManagerMock.system.hot_water
    hot_water.operation_mode = HeatingMode.OFF
    SystemManagerMock.instance.get_hot_water.return_value = hot_water

    await hass.services.async_call('water_heater',
                                   'set_away_mode',
                                   {
                                       'entity_id':
                                           'water_heater.vaillant_hot_water',
                                       'away_mode': True
                                   })
    await hass.async_block_till_done()

    SystemManagerMock.instance.set_hot_water_operation_mode.\
        assert_called_once_with(ANY, HeatingMode.OFF)
    _assert_state(hass, HeatingMode.OFF, HotWater.MIN_TEMP, 45, 'on')


async def test_turn_away_mode_off(hass):
    """Test turn away mode off."""
    assert await _setup(hass)

    hot_water = SystemManagerMock.system.hot_water
    hot_water.operation_mode = HeatingMode.AUTO
    SystemManagerMock.instance.get_hot_water.return_value = hot_water

    await hass.services.async_call('water_heater',
                                   'set_away_mode',
                                   {
                                       'entity_id':
                                           'water_heater.vaillant_hot_water',
                                       'away_mode': False
                                   })
    await hass.async_block_till_done()

    SystemManagerMock.instance.set_hot_water_operation_mode.\
        assert_called_once_with(ANY, HeatingMode.AUTO)

    _assert_state(hass, HeatingMode.AUTO, HotWater.MIN_TEMP, 45, 'off')


async def test_set_operation_mode(hass):
    """Test set operation mode."""
    assert await _setup(hass)

    hot_water = SystemManagerMock.system.hot_water
    hot_water.operation_mode = HeatingMode.ON
    SystemManagerMock.instance.get_hot_water.return_value = hot_water

    await hass.services.async_call('water_heater',
                                   'set_operation_mode',
                                   {
                                       'entity_id':
                                           'water_heater.vaillant_hot_water',
                                       'operation_mode': 'ON'
                                   })
    await hass.async_block_till_done()

    SystemManagerMock.instance.set_hot_water_operation_mode\
        .assert_called_once_with(ANY, HeatingMode.ON)
    _assert_state(hass, HeatingMode.ON, 40, 45, 'off')


async def test_set_operation_mode_wrong(hass):
    """Test set operation mode with wrong mode."""
    assert await _setup(hass)

    await hass.services.async_call('water_heater',
                                   'set_operation_mode',
                                   {
                                       'entity_id':
                                           'water_heater.vaillant_hot_water',
                                       'operation_mode': 'wrong'
                                   })
    await hass.async_block_till_done()

    SystemManagerMock.instance.set_hot_water_operation_mode\
        .assert_not_called()
    _assert_state(hass, HeatingMode.AUTO, HotWater.MIN_TEMP, 45, 'off')


async def test_set_temperature(hass):
    """Test set target temperature."""
    system = SystemManagerMock.get_default_system()
    system.hot_water.operation_mode = HeatingMode.ON
    assert await _setup(hass, system=system)

    SystemManagerMock.system.hot_water.target_temperature = 50
    SystemManagerMock.instance.get_hot_water.return_value = \
        SystemManagerMock.system.hot_water

    await hass.services.async_call('water_heater',
                                   'set_temperature',
                                   {
                                       'entity_id':
                                           'water_heater.vaillant_hot_water',
                                       'temperature': 50
                                   })
    await hass.async_block_till_done()

    SystemManagerMock.instance.set_hot_water_setpoint_temperature \
        .assert_called_once_with(ANY, 50)
    _assert_state(hass, HeatingMode.ON, 50, 45, 'off')
