"""Test the Home Assistant analytics sensor module."""
from unittest.mock import AsyncMock, patch

import pytest
from syrupy import SnapshotAssertion

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry


@pytest.mark.freeze_time("2023-10-21")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    mock_analytics_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch(
        "homeassistant.components.homeassistant_analytics.PLATFORMS", [Platform.SENSOR]
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
