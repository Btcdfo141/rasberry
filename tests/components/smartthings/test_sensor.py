"""
Test for the SmartThings sensors platform.

The only mocking required is of the underlying SmartThings API object so
real HTTP calls are not initiated during testing.
"""
from pysmartthings import Attribute, Capability, CAPABILITIES, ATTRIBUTES

from homeassistant.components.sensor import DEVICE_CLASSES, DOMAIN as SENSOR_DOMAIN
from homeassistant.components.smartthings import sensor
from homeassistant.components.smartthings.const import (
    DOMAIN, SIGNAL_SMARTTHINGS_UPDATE)
from homeassistant.const import ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .conftest import setup_platform


async def test_mapping_integrity():
    """Test ensures the map dicts have proper integrity."""
    for capability, maps in sensor.CAPABILITY_TO_SENSORS.items():
        assert capability in CAPABILITIES, capability
        for map in maps:
            assert map.attribute in ATTRIBUTES, map.attribute
            if map.device_class:
                assert map.device_class in DEVICE_CLASSES, map.device_class


async def test_async_setup_platform():
    """Test setup platform does nothing (it uses config entries)."""
    await sensor.async_setup_platform(None, None, None)


async def test_entity_state(hass, device_factory):
    """Tests the state attributes properly match the light types."""
    device = device_factory('Sensor 1', [Capability.battery],
                            {Attribute.battery: 100})
    await setup_platform(hass, SENSOR_DOMAIN, device)
    state = hass.states.get('sensor.sensor_1_battery')
    assert state.state == '100'
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == '%'
    assert state.attributes[ATTR_FRIENDLY_NAME] ==\
        device.label + " Battery"


async def test_entity_and_device_attributes(hass, device_factory):
    """Test the attributes of the entity are correct."""
    # Arrange
    device = device_factory('Sensor 1', [Capability.battery],
                            {Attribute.battery: 100})
    entity_registry = await hass.helpers.entity_registry.async_get_registry()
    device_registry = await hass.helpers.device_registry.async_get_registry()
    # Act
    await setup_platform(hass, SENSOR_DOMAIN, device)
    # Assert
    entry = entity_registry.async_get('sensor.sensor_1_battery')
    assert entry
    assert entry.unique_id == device.device_id + '.' + Attribute.battery
    entry = device_registry.async_get_device(
        {(DOMAIN, device.device_id)}, [])
    assert entry
    assert entry.name == device.label
    assert entry.model == device.device_type_name
    assert entry.manufacturer == 'Unavailable'


async def test_update_from_signal(hass, device_factory):
    """Test the binary_sensor updates when receiving a signal."""
    # Arrange
    device = device_factory('Sensor 1', [Capability.battery],
                            {Attribute.battery: 100})
    await setup_platform(hass, SENSOR_DOMAIN, device)
    device.status.apply_attribute_update(
        'main', Capability.battery, Attribute.battery, 75)
    # Act
    async_dispatcher_send(hass, SIGNAL_SMARTTHINGS_UPDATE,
                          [device.device_id])
    # Assert
    await hass.async_block_till_done()
    state = hass.states.get('sensor.sensor_1_battery')
    assert state is not None
    assert state.state == '75'


async def test_unload_config_entry(hass, device_factory):
    """Test the binary_sensor is removed when the config entry is unloaded."""
    # Arrange
    device = device_factory('Sensor 1', [Capability.battery],
                            {Attribute.battery: 100})
    config_entry = await setup_platform(hass, SENSOR_DOMAIN, device)
    # Act
    await hass.config_entries.async_forward_entry_unload(
        config_entry, 'sensor')
    # Assert
    assert not hass.states.get('sensor.sensor_1_battery')
