"""Test HomeKit util module."""
import pytest
import voluptuous as vol

from homeassistant.components.homekit.const import (
    CONF_FEATURE, CONF_FEATURE_LIST, HOMEKIT_NOTIFY_ID)
from homeassistant.components.homekit.util import (
    convert_to_float, density_to_air_quality, dismiss_setup_message,
    show_setup_message, temperature_to_homekit, temperature_to_states,
    validate_media_player_features)
from homeassistant.components.homekit.util import validate_entity_config \
    as vec
from homeassistant.components.persistent_notification import (
    ATTR_MESSAGE, ATTR_NOTIFICATION_ID)
from homeassistant.const import (
    ATTR_CODE, ATTR_SUPPORTED_FEATURES, CONF_NAME, CONF_TYPE)
from homeassistant.core import State

from tests.common import async_mock_service


def test_validate_entity_config():
    """Test validate entities."""
    configs = [{'invalid_entity_id': {}}, {'demo.test': 1},
               {'demo.test': 'test'}, {'demo.test': [1, 2]},
               {'demo.test': None}, {'demo.test': {CONF_NAME: None}},
               {'media_player.test': {CONF_FEATURE_LIST: [
                    {CONF_FEATURE: 'invalid_feature'}]}},
               {'media_player.test': {CONF_FEATURE_LIST: [
                    {CONF_FEATURE: 'on_off'},
                    {CONF_FEATURE: 'on_off'}]}},
               {'switch.test': {CONF_TYPE: 'invalid_type'}}]

    for conf in configs:
        with pytest.raises(vol.Invalid):
            vec(conf)

    assert vec({}) == {}
    assert vec({'demo.test': {CONF_NAME: 'Name'}}) == \
        {'demo.test': {CONF_NAME: 'Name'}}

    assert vec({'alarm_control_panel.demo': {}}) == \
        {'alarm_control_panel.demo': {ATTR_CODE: None}}
    assert vec({'alarm_control_panel.demo': {ATTR_CODE: '1234'}}) == \
        {'alarm_control_panel.demo': {ATTR_CODE: '1234'}}

    assert vec({'lock.demo': {}}) == {'lock.demo': {ATTR_CODE: None}}
    assert vec({'lock.demo': {ATTR_CODE: '1234'}}) == \
        {'lock.demo': {ATTR_CODE: '1234'}}

    assert vec({'media_player.demo': {}}) == \
        {'media_player.demo': {CONF_FEATURE_LIST: {}}}
    config = {CONF_FEATURE_LIST: [{CONF_FEATURE: 'on_off'},
                                  {CONF_FEATURE: 'play_pause'}]}
    assert vec({'media_player.demo': config}) == \
        {'media_player.demo': {CONF_FEATURE_LIST:
                               {'on_off': {}, 'play_pause': {}}}}
    assert vec({'switch.demo': {CONF_TYPE: 'outlet'}}) == \
        {'switch.demo': {CONF_TYPE: 'outlet'}}


def test_validate_media_player_features():
    """Test validate modes for media players."""
    config = {}
    attrs = {ATTR_SUPPORTED_FEATURES: 20873}
    entity_state = State('media_player.demo', 'on', attrs)
    assert validate_media_player_features(entity_state, config) is True

    config = {'on_off': None}
    assert validate_media_player_features(entity_state, config) is True

    entity_state = State('media_player.demo', 'on')
    assert validate_media_player_features(entity_state, config) is False


def test_convert_to_float():
    """Test convert_to_float method."""
    assert convert_to_float(12) == 12
    assert convert_to_float(12.4) == 12.4
    assert convert_to_float('unknown') is None
    assert convert_to_float(None) is None


def test_temperature_to_homekit():
    """Test temperature conversion from HA to HomeKit."""
    assert temperature_to_homekit(20.46, '°C') == 20.5
    assert temperature_to_homekit(92.1, '°F') == 33.4


def test_temperature_to_states():
    """Test temperature conversion from HomeKit to HA."""
    assert temperature_to_states(20, '°C') == 20.0
    assert temperature_to_states(20.2, '°F') == 68.4


def test_density_to_air_quality():
    """Test map PM2.5 density to HomeKit AirQuality level."""
    assert density_to_air_quality(0) == 1
    assert density_to_air_quality(35) == 1
    assert density_to_air_quality(35.1) == 2
    assert density_to_air_quality(75) == 2
    assert density_to_air_quality(115) == 3
    assert density_to_air_quality(150) == 4
    assert density_to_air_quality(300) == 5


async def test_show_setup_msg(hass):
    """Test show setup message as persistence notification."""
    pincode = b'123-45-678'

    call_create_notification = \
        async_mock_service(hass, 'persistent_notification', 'create')

    await hass.async_add_job(show_setup_message, hass, pincode)
    await hass.async_block_till_done()

    assert call_create_notification
    assert call_create_notification[0].data[ATTR_NOTIFICATION_ID] == \
        HOMEKIT_NOTIFY_ID
    assert pincode.decode() in call_create_notification[0].data[ATTR_MESSAGE]


async def test_dismiss_setup_msg(hass):
    """Test dismiss setup message."""
    call_dismiss_notification = \
        async_mock_service(hass, 'persistent_notification', 'dismiss')

    await hass.async_add_job(dismiss_setup_message, hass)
    await hass.async_block_till_done()

    assert call_dismiss_notification
    assert call_dismiss_notification[0].data[ATTR_NOTIFICATION_ID] == \
        HOMEKIT_NOTIFY_ID
