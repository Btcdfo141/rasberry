"""Tests for Shelly button platform."""
from __future__ import annotations

from pytest_unordered import unordered

from homeassistant.components.event import (
    ATTR_EVENT_TYPE,
    ATTR_EVENT_TYPES,
    EventDeviceClass,
)
from homeassistant.const import ATTR_DEVICE_CLASS, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get

from . import init_integration, inject_rpc_device_event


async def test_rpc_button(hass: HomeAssistant, mock_rpc_device, monkeypatch) -> None:
    """Test RPC device event."""
    await init_integration(hass, 2)
    entity_id = "event.test_switch_0"
    registry = async_get(hass)

    state = hass.states.get(entity_id)
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_EVENT_TYPES) == unordered(
        ["btn_down", "btn_up", "double_push", "long_push", "single_push", "triple_push"]
    )
    assert state.attributes.get(ATTR_EVENT_TYPE) is None
    assert state.attributes.get(ATTR_DEVICE_CLASS) == EventDeviceClass.BUTTON

    entry = registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "123456789ABC-input:0"

    inject_rpc_device_event(
        monkeypatch,
        mock_rpc_device,
        {
            "events": [
                {
                    "event": "single_push",
                    "id": 0,
                    "ts": 1668522399.2,
                }
            ],
            "ts": 1668522399.2,
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.attributes.get(ATTR_EVENT_TYPE) == "single_push"
