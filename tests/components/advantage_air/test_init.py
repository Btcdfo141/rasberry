"""Test the Advantage Air Initialization."""
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from . import add_mock_config


async def test_async_setup_entry(hass: HomeAssistant) -> None:
    """Test a successful setup entry and unload."""

    entry = await add_mock_config(hass)
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_async_setup_entry_failure(hass: HomeAssistant) -> None:
    """Test a unsuccessful setup entry."""

    entry = await add_mock_config(hass, get_side_effect=SyntaxError)
    assert entry.state is ConfigEntryState.SETUP_RETRY
