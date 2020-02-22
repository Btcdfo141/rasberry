"""Test Dynalite cover."""
from dynalite_devices_lib.cover import DynaliteTimeCoverWithTiltDevice
import pytest

from .common import (
    ATTR_ARGS,
    ATTR_METHOD,
    ATTR_SERVICE,
    create_entity_from_device,
    create_mock_device,
    get_bridge_from_hass,
    run_service_tests,
)


@pytest.fixture
def mock_device():
    """Mock a Dynalite device."""
    return create_mock_device("cover", DynaliteTimeCoverWithTiltDevice)


async def test_cover_setup(hass, mock_device):
    """Test a successful setup."""
    await create_entity_from_device(hass, mock_device)
    entity_state = hass.states.get("cover.name")
    assert entity_state.attributes["friendly_name"] == mock_device.name
    assert (
        entity_state.attributes["current_position"]
        == mock_device.current_cover_position
    )
    assert (
        entity_state.attributes["current_tilt_position"]
        == mock_device.current_cover_tilt_position
    )
    assert entity_state.attributes["device_class"] == mock_device.device_class
    await run_service_tests(
        hass,
        mock_device,
        "cover",
        [
            {ATTR_SERVICE: "open_cover", ATTR_METHOD: "async_open_cover"},
            {ATTR_SERVICE: "close_cover", ATTR_METHOD: "async_close_cover"},
            {ATTR_SERVICE: "stop_cover", ATTR_METHOD: "async_stop_cover"},
            {
                ATTR_SERVICE: "set_cover_position",
                ATTR_METHOD: "async_set_cover_position",
                ATTR_ARGS: {"position": 50},
            },
            {ATTR_SERVICE: "open_cover_tilt", ATTR_METHOD: "async_open_cover_tilt"},
            {ATTR_SERVICE: "close_cover_tilt", ATTR_METHOD: "async_close_cover_tilt"},
            {ATTR_SERVICE: "stop_cover_tilt", ATTR_METHOD: "async_stop_cover_tilt"},
            {
                ATTR_SERVICE: "set_cover_tilt_position",
                ATTR_METHOD: "async_set_cover_tilt_position",
                ATTR_ARGS: {"tilt_position": 50},
            },
        ],
    )


async def test_cover_without_tilt(hass, mock_device):
    """Test a cover with no tilt."""
    mock_device.has_tilt = False
    await create_entity_from_device(hass, mock_device)
    await hass.services.async_call(
        "cover", "open_cover_tilt", {"entity_id": "cover.name"}, blocking=True
    )
    await hass.async_block_till_done()
    mock_device.async_open_cover_tilt.assert_not_called()


async def check_cover_position(
    bridge, device, hass_obj, closing, opening, closed, expected
):
    """Check that a given position behaves correctly."""
    device.is_closing = closing
    device.is_opening = opening
    device.is_closed = closed
    bridge.update_device(device)
    await hass_obj.async_block_till_done()
    entity_state = hass_obj.states.get("cover.name")
    assert entity_state.state == expected


async def test_cover_positions(hass, mock_device):
    """Test that the state updates in the various positions."""
    await create_entity_from_device(hass, mock_device)
    # Get the bridge to update HA
    bridge = get_bridge_from_hass(hass)
    await check_cover_position(bridge, mock_device, hass, True, False, False, "closing")
    await check_cover_position(bridge, mock_device, hass, False, True, False, "opening")
    await check_cover_position(bridge, mock_device, hass, False, False, True, "closed")
    await check_cover_position(bridge, mock_device, hass, False, False, False, "open")
