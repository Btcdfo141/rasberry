"""Test Z-Wave fans."""
import pytest

from homeassistant.components.fan import SUPPORT_SET_SPEED
from homeassistant.components.zwave import fan

from tests.mock.zwave import MockEntityValues, MockNode, MockValue

# Integration is disabled
pytest.skip("Integration has been disabled in the manifest", allow_module_level=True)


def test_get_device_detects_fan(mock_openzwave):
    """Test get_device returns a zwave fan."""
    node = MockNode()
    value = MockValue(data=0, node=node)
    values = MockEntityValues(primary=value)

    device = fan.get_device(node=node, values=values, node_config={})
    assert isinstance(device, fan.ZwaveFan)
    assert device.supported_features == SUPPORT_SET_SPEED


def test_fan_turn_on(mock_openzwave):
    """Test turning on a zwave fan."""
    node = MockNode()
    value = MockValue(data=0, node=node)
    values = MockEntityValues(primary=value)
    device = fan.get_device(node=node, values=values, node_config={})

    device.turn_on()

    assert node.set_dimmer.called
    value_id, brightness = node.set_dimmer.mock_calls[0][1]
    assert value_id == value.value_id
    assert brightness == 255

    node.reset_mock()

    device.turn_on(percentage=0)

    assert node.set_dimmer.called
    value_id, brightness = node.set_dimmer.mock_calls[0][1]

    assert value_id == value.value_id
    assert brightness == 0

    node.reset_mock()

    device.turn_on(percentage=1)

    assert node.set_dimmer.called
    value_id, brightness = node.set_dimmer.mock_calls[0][1]

    assert value_id == value.value_id
    assert brightness == 1

    node.reset_mock()

    device.turn_on(percentage=50)

    assert node.set_dimmer.called
    value_id, brightness = node.set_dimmer.mock_calls[0][1]

    assert value_id == value.value_id
    assert brightness == 50

    node.reset_mock()

    device.turn_on(percentage=100)

    assert node.set_dimmer.called
    value_id, brightness = node.set_dimmer.mock_calls[0][1]

    assert value_id == value.value_id
    assert brightness == 99


def test_fan_turn_off(mock_openzwave):
    """Test turning off a dimmable zwave fan."""
    node = MockNode()
    value = MockValue(data=46, node=node)
    values = MockEntityValues(primary=value)
    device = fan.get_device(node=node, values=values, node_config={})

    device.turn_off()

    assert node.set_dimmer.called
    value_id, brightness = node.set_dimmer.mock_calls[0][1]
    assert value_id == value.value_id
    assert brightness == 0
