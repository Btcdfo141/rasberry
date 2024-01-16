"""Test init of ecovacs."""
from typing import Any
from unittest.mock import Mock, patch

from deebot_client.exceptions import DeebotError, InvalidAuthenticationError
import pytest

from homeassistant.components.ecovacs.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .const import VALID_ENTRY_DATA

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("mock_api_client")
async def test_load_unload_config_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test loading and unloading the integration."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_config_entry_not_ready(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: Mock,
) -> None:
    """Test the Ecovacs configuration entry not ready."""
    mock_api_client.get_devices.side_effect = DeebotError

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_invalid_auth(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api_client: Mock,
) -> None:
    """Test auth error during setup."""
    mock_api_client.get_devices.side_effect = InvalidAuthenticationError
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


@pytest.mark.parametrize(
    ("config", "expect_call"),
    [
        ({}, False),
        ({DOMAIN: VALID_ENTRY_DATA}, True),
    ],
)
async def test_async_setup_import(
    hass: HomeAssistant, config: dict[str, Any], expect_call: bool
) -> None:
    """Test async_setup config import."""
    with patch.object(hass.config_entries.flow, "async_init", autospec=True) as mock:
        assert await async_setup_component(hass, DOMAIN, config)
        if expect_call:
            mock.assert_called_once()
        else:
            mock.assert_not_called()
