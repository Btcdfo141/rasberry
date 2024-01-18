"""Test the Home Assistant analytics sensor module."""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from python_homeassistant_analytics import (
    HomeassistantAnalyticsConnectionError,
    HomeassistantAnalyticsNotModifiedError,
)
from syrupy import SnapshotAssertion

from homeassistant.const import STATE_UNAVAILABLE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_all_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    mock_analytics_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch(
        "homeassistant.components.analytics_insights.PLATFORMS",
        [Platform.SENSOR],
    ):
        await setup_integration(hass, mock_config_entry)
        entity_entries = er.async_entries_for_config_entry(
            entity_registry, mock_config_entry.entry_id
        )

        assert entity_entries
        for entity_entry in entity_entries:
            assert hass.states.get(entity_entry.entity_id) == snapshot(
                name=f"{entity_entry.entity_id}-state"
            )
            assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")


async def test_connection_error(
    hass: HomeAssistant,
    mock_analytics_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test connection error."""
    await setup_integration(hass, mock_config_entry)

    mock_analytics_client.return_value.get_current_analytics.side_effect = (
        HomeassistantAnalyticsConnectionError()
    )
    freezer.tick(delta=timedelta(hours=12))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert (
        hass.states.get("sensor.homeassistant_analytics_spotify").state
        == STATE_UNAVAILABLE
    )


async def test_data_not_modified(
    hass: HomeAssistant,
    mock_analytics_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test not updating data if its not modified."""
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get("sensor.homeassistant_analytics_spotify").state == "24388"
    mock_analytics_client.return_value.get_current_analytics.side_effect = (
        HomeassistantAnalyticsNotModifiedError()
    )
    freezer.tick(delta=timedelta(hours=12))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.homeassistant_analytics_spotify").state == "24388"
