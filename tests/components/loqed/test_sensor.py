"""Tests the sensor platform of the Loqed integration."""
from homeassistant.components.loqed import LoqedDataCoordinator
from homeassistant.components.loqed.const import DOMAIN
from homeassistant.components.sensor import (
    ATTR_STATE_CLASS,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT, PERCENTAGE
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_battery_sensor(
    hass: HomeAssistant,
    integration: MockConfigEntry,
) -> None:
    """Test the battery sensor."""
    entity_id = "sensor.battery"

    state = hass.states.get(entity_id)

    assert state
    assert state.state == "78"
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.BATTERY
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert state.attributes[ATTR_STATE_CLASS] is SensorStateClass.MEASUREMENT


async def test_battery_sensor_update(
    hass: HomeAssistant, integration: MockConfigEntry
) -> None:
    """Tests the sensor responding to a coordinator update."""

    entity_id = "sensor.battery"

    coordinator: LoqedDataCoordinator = hass.data[DOMAIN][integration.entry_id]
    coordinator.async_set_updated_data({"battery_percentage": 99})

    state = hass.states.get(entity_id)
    assert state.state == "99"
