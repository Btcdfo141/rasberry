"""Test different accessory types: Triggers (Programmable Switches)."""

from unittest.mock import MagicMock

from homeassistant.components.homekit.type_triggers import DeviceTriggerAccessory
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry, async_get_device_automations


async def test_programmable_switch_button_fires_on_trigger(
    hass, hk_driver, events, demo_cleanup, device_reg, entity_reg
):
    """Test that DeviceTriggerAccessory fires the programmable switch event on trigger."""
    hk_driver.publish = MagicMock()

    demo_config_entry = MockConfigEntry(domain="domain")
    demo_config_entry.add_to_hass(hass)
    assert await async_setup_component(hass, "demo", {"demo": {}})
    await hass.async_block_till_done()
    hass.states.async_set("light.ceiling_lights", STATE_OFF)
    await hass.async_block_till_done()

    entry = entity_reg.async_get("light.ceiling_lights")
    assert entry is not None
    device_id = entry.device_id

    device_triggers = await async_get_device_automations(hass, "trigger", device_id)
    acc = DeviceTriggerAccessory(
        hass,
        hk_driver,
        "DeviceTriggerAccessory",
        None,
        1,
        None,
        device_id=device_id,
        device_triggers=device_triggers,
    )
    await acc.run()
    await hass.async_block_till_done()

    assert acc.entity_id is None
    assert acc.device_id is device_id
    assert acc.available is True

    hk_driver.publish.reset_mock()
    hass.states.async_set("light.ceiling_lights", STATE_ON)
    await hass.async_block_till_done()
    hk_driver.publish.assert_called_once()

    hk_driver.publish.reset_mock()
    hass.states.async_set("light.ceiling_lights", STATE_OFF)
    await hass.async_block_till_done()
    hk_driver.publish.assert_called_once()

    await acc.stop()
