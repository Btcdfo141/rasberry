"""Test the Blink init."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientError
import pytest

from homeassistant.components.blink.const import (
    DOMAIN,
    SERVICE_REFRESH,
    SERVICE_SAVE_RECENT_CLIPS,
    SERVICE_SAVE_VIDEO,
    SERVICE_SEND_PIN,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_FILE_PATH, CONF_FILENAME, CONF_NAME, CONF_PIN
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_setup_entry(
    hass: HomeAssistant,
    blink_api: MagicMock,
    blink_auth_api: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup entry."""
    blink_api.return_value = blink_api
    blink_auth_api.return_value = blink_auth_api

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_setup_not_ready_client_error(
    hass: HomeAssistant,
    blink_api: MagicMock,
    blink_auth_api: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup failed because we can't connect to the Blink system."""
    blink_api.start = AsyncMock(side_effect=ClientError)
    blink_api.return_value = blink_api
    blink_auth_api.return_value = blink_auth_api

    mock_config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_not_ready_timeout_error(
    hass: HomeAssistant,
    blink_api: MagicMock,
    blink_auth_api: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup failed because we can't connect to the Blink system."""
    blink_api.refresh = AsyncMock(side_effect=asyncio.TimeoutError)
    blink_api.return_value = blink_api
    blink_auth_api.return_value = blink_auth_api

    mock_config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_not_ready_authkey_required(
    hass: HomeAssistant,
    blink_api: MagicMock,
    blink_auth_api: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup failed because 2FA is needed to connect to the Blink system."""
    blink_api.return_value = blink_api
    blink_auth_api.check_key_required = MagicMock(return_value=True)
    blink_auth_api.return_value = blink_auth_api

    mock_config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_not_ready_not_available(
    hass: HomeAssistant,
    blink_api: MagicMock,
    blink_auth_api: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup failed because Blink system is not available."""
    blink_api.available = False
    blink_api.return_value = blink_api
    blink_auth_api.return_value = blink_auth_api

    mock_config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(
    hass: HomeAssistant,
    blink_api: MagicMock,
    blink_auth_api: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test being able to unload an entry."""

    blink_api.return_value = blink_api
    blink_auth_api.return_value = blink_auth_api

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_migrate_V0(
    hass: HomeAssistant,
    blink_api: MagicMock,
    blink_auth_api: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test migration script version 0."""

    blink_api.return_value = blink_api
    blink_auth_api.return_value = blink_auth_api
    mock_config_entry.version = 0

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.parametrize(("version"), [1, 2])
async def test_migrate(
    hass: HomeAssistant,
    blink_api: MagicMock,
    blink_auth_api: MagicMock,
    mock_config_entry: MockConfigEntry,
    version,
) -> None:
    """Test migration scripts."""

    blink_api.return_value = blink_api
    blink_auth_api.return_value = blink_auth_api
    mock_config_entry.version = version
    mock_config_entry.data = {**mock_config_entry.data, "login_response": "Blah"}

    mock_config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()


async def test_service_calls(
    hass: HomeAssistant,
    blink_api: MagicMock,
    blink_auth_api: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup entry."""
    blink_api.return_value = blink_api
    blink_auth_api.return_value = blink_auth_api

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert blink_api.refresh.call_count == 1

    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH,
        blocking=True,
    )

    assert blink_api.refresh.call_count == 2

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SAVE_VIDEO,
        {CONF_NAME: "Camera 1", CONF_FILENAME: "Blah"},
        blocking=True,
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SAVE_RECENT_CLIPS,
        {CONF_NAME: "Camera 1", CONF_FILE_PATH: "Blah"},
        blocking=True,
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SEND_PIN,
        {CONF_PIN: "1234"},
        blocking=True,
    )
