"""Test the Trend integration."""
from homeassistant.components.trend.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def test_setup_and_remove_config_entry(hass: HomeAssistant) -> None:
    """Test setting up and removing a config entry."""
    registry = er.async_get(hass)
    trend_entity_id = "binary_sensor.my_trend"

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "name": "My trend",
            "entity_id": "sensor.cpu_temp",
            "invert": False,
            "max_samples": 2.0,
            "min_gradient": 0.0,
            "sample_duration": 0.0,
        },
        title="My trend",
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the entity is registered in the entity registry
    assert registry.async_get(trend_entity_id) is not None

    # Update the entry
    hass.config_entries.async_update_entry(
        config_entry, options={**config_entry.data, "max_samples": 4.0}
    )
    await hass.async_block_till_done()

    # Check the entity is still registered in the entity registry
    assert registry.async_get(trend_entity_id) is not None

    # Remove the config entry
    assert await hass.config_entries.async_remove(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the state and entity registry entry are removed
    assert hass.states.get(trend_entity_id) is None
    assert registry.async_get(trend_entity_id) is None
