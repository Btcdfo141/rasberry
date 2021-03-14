"""The tests for RFXCOM RFXtrx device triggers."""
from typing import NamedTuple, Set, Tuple

import pytest

import homeassistant.components.automation as automation
from homeassistant.components.rfxtrx import DOMAIN
from homeassistant.setup import async_setup_component

from tests.common import (
    MockConfigEntry,
    assert_lists_same,
    async_get_device_automations,
    async_mock_service,
    mock_device_registry,
)
from tests.components.rfxtrx.conftest import create_rfx_test_cfg


class EventTestData(NamedTuple):
    """Test data linked to a device."""

    code: str
    device_identifiers: Set[Tuple[str]]
    type: str
    subtype: str


DEVICE_LIGHTING_1 = {("rfxtrx", "10", "0", "E5")}
EVENT_LIGHTING_1 = EventTestData("0710002a45050170", DEVICE_LIGHTING_1, "command", "On")

DEVICE_ROLLERTROL_1 = {("rfxtrx", "19", "0", "009ba8:1")}
EVENT_ROLLERTROL_1 = EventTestData(
    "09190000009ba8010100", DEVICE_ROLLERTROL_1, "command", "Down"
)


@pytest.fixture(name="device_reg")
def device_reg_fixture(hass):
    """Return an empty, loaded, registry."""
    return mock_device_registry(hass)


async def setup_entry(hass, devices):
    """Construct a config setup."""
    entry_data = create_rfx_test_cfg(devices=devices)
    mock_entry = MockConfigEntry(domain="rfxtrx", unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()


@pytest.mark.parametrize(
    "event,expected",
    [
        [
            EVENT_LIGHTING_1,
            [
                {"type": "command", "subtype": subtype}
                for subtype in [
                    "Off",
                    "On",
                    "Dim",
                    "Bright",
                    "All/group Off",
                    "All/group On",
                    "Chime",
                    "Illegal command",
                ]
            ],
        ]
    ],
)
async def test_get_triggers(hass, device_reg, event: EventTestData, expected):
    """Test we get the expected triggers from a rfxtrx."""
    await setup_entry(hass, {event.code: {"signal_repetitions": 1}})

    device_entry = device_reg.async_get_device(event.device_identifiers, set())

    expected_triggers = [
        {"domain": DOMAIN, "device_id": device_entry.id, "platform": "device", **expect}
        for expect in expected
    ]

    triggers = await async_get_device_automations(hass, "trigger", device_entry.id)
    triggers = [value for value in triggers if value["domain"] == "rfxtrx"]
    assert_lists_same(triggers, expected_triggers)


@pytest.mark.parametrize(
    "event",
    [
        EVENT_LIGHTING_1,
        EVENT_ROLLERTROL_1,
    ],
)
async def test_firing_event(hass, device_reg, rfxtrx, event):
    """Test for turn_on and turn_off triggers firing."""

    await setup_entry(hass, {event.code: {"fire_event": True, "signal_repetitions": 1}})

    device_entry = device_reg.async_get_device(event.device_identifiers, set())

    calls = async_mock_service(hass, "test", "automation")

    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "type": event.type,
                        "subtype": event.subtype,
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {"some": ("{{trigger.platform}}")},
                    },
                },
            ]
        },
    )
    await hass.async_block_till_done()

    await rfxtrx.signal(event.code)

    assert len(calls) == 1
    assert calls[0].data["some"] == "device"
