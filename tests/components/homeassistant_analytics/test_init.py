"""Test the Home Assistant analytics init module."""
from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.components.homeassistant_analytics.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry
from tests.components.homeassistant_analytics import setup_integration


async def test_load_unload_entry(
    hass: HomeAssistant,
    mock_analytics_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test load and unload entry."""
    await setup_integration(hass, mock_config_entry)
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    assert entry.state == ConfigEntryState.LOADED

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.NOT_LOADED
