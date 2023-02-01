"""Define tests for the NSW Rural Fire Service Feeds general setup."""
from unittest.mock import patch

from homeassistant.components.nsw_rural_fire_service_feed.const import DOMAIN, FEED
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import async_entries_for_config_entry

from tests.components.nsw_rural_fire_service_feed import _generate_mock_feed_entry


async def test_component_unload_config_entry(hass, config_entry):
    """Test that loading and unloading of a config entry works."""
    config_entry.add_to_hass(hass)
    with patch(
        "aio_geojson_nsw_rfs_incidents.NswRuralFireServiceIncidentsFeedManager.update"
    ) as mock_feed_manager_update:
        # Load config entry.
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        assert mock_feed_manager_update.call_count == 1
        assert hass.data[DOMAIN][FEED][config_entry.entry_id] is not None
        # Unload config entry.
        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()
        assert hass.data[DOMAIN][FEED].get(config_entry.entry_id) is None


async def test_remove_orphaned_entities(hass, config_entry):
    """Test removing orphaned geolocation entities."""
    config_entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        "geo_location", "geo_json_events", "1", config_entry=config_entry
    )
    entity_registry.async_get_or_create(
        "geo_location", "geo_json_events", "2", config_entry=config_entry
    )
    entity_registry.async_get_or_create(
        "geo_location", "geo_json_events", "3", config_entry=config_entry
    )

    # There should now be 3 "orphaned" entries available which will be removed
    # when the component is set up.
    entries = async_entries_for_config_entry(entity_registry, config_entry.entry_id)
    assert len(entries) == 3

    # Set up a mock feed entry for this test.
    mock_entry_1 = _generate_mock_feed_entry(
        "1234",
        "Title 1",
        15.5,
        (38.0, -3.0),
    )

    with patch(
        "aio_geojson_nsw_rfs_incidents.feed.NswRuralFireServiceIncidentsFeed.update"
    ) as mock_feed_update:
        mock_feed_update.return_value = "OK", [mock_entry_1]
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # 1 geolocation entity remaining.
        entries = async_entries_for_config_entry(entity_registry, config_entry.entry_id)
        assert len(entries) == 1

        assert len(hass.states.async_entity_ids("geo_location")) == 1
