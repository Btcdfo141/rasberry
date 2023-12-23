"""Test DROP select entities."""

from homeassistant.components.drop_connect.const import DOMAIN
from homeassistant.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .common import TEST_DATA_HUB, TEST_DATA_HUB_RESET, TEST_DATA_HUB_TOPIC

from tests.common import async_fire_mqtt_message
from tests.typing import MqttMockHAClient


async def test_selects_hub(
    hass: HomeAssistant, config_entry_hub, mqtt_mock: MqttMockHAClient
) -> None:
    """Test DROP binary sensors for hubs."""
    config_entry_hub.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    protect_mode_select_name = "select.hub_drop_1_c0ffee_protect_mode"
    protect_mode_select = hass.states.get(protect_mode_select_name)
    assert protect_mode_select
    assert protect_mode_select.attributes.get(ATTR_OPTIONS) == [
        "AWAY",
        "HOME",
        "SCHEDULE",
    ]
    assert protect_mode_select.state == "HOME"

    async_fire_mqtt_message(hass, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB_RESET)
    await hass.async_block_till_done()
    async_fire_mqtt_message(hass, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB)
    await hass.async_block_till_done()

    protect_mode_select = hass.states.get(protect_mode_select_name)
    assert protect_mode_select
    assert protect_mode_select.state == "HOME"

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_OPTION: "AWAY", ATTR_ENTITY_ID: protect_mode_select_name},
        blocking=True,
    )
    await hass.async_block_till_done()

    async_fire_mqtt_message(hass, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB_RESET)
    await hass.async_block_till_done()

    protect_mode_select = hass.states.get(protect_mode_select_name)
    assert protect_mode_select
    assert protect_mode_select.state == "AWAY"
