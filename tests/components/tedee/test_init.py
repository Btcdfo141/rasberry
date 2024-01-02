"""Test initialization of tedee."""
from http import HTTPStatus
from typing import Any
from unittest.mock import MagicMock
from urllib.parse import urlparse

from freezegun.api import FrozenDateTimeFactory
from pytedee_async.exception import (
    TedeeAuthException,
    TedeeClientException,
    TedeeWebhookException,
)
import pytest

from homeassistant.components.webhook import async_generate_url
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant

from .conftest import WEBHOOK_ID

from tests.common import MockConfigEntry
from tests.typing import ClientSessionGenerator


async def test_load_unload_config_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_tedee: MagicMock,
) -> None:
    """Test loading and unloading the integration."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    "side_effect", [TedeeClientException(""), TedeeAuthException("")]
)
async def test_config_entry_not_ready(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_tedee: MagicMock,
    side_effect: Exception,
) -> None:
    """Test the LaMetric configuration entry not ready."""
    mock_tedee.get_locks.side_effect = side_effect

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert len(mock_tedee.get_locks.mock_calls) == 1
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_cleanup_on_shutdown(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_tedee: MagicMock,
) -> None:
    """Test the socket is cleaned up on shutdown."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    mock_tedee.delete_webhooks.assert_called_once()


@pytest.mark.parametrize(
    ("body", "expected_code", "side_effect"),
    [
        ({"hello": "world"}, HTTPStatus.OK, None),  # Success
        (None, HTTPStatus.BAD_REQUEST, None),  # Missing data
        ({}, HTTPStatus.BAD_REQUEST, TedeeWebhookException),  # Error
    ],
)
async def test_webhook_post(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_tedee: MagicMock,
    hass_client_no_auth: ClientSessionGenerator,
    body: dict[str, Any],
    expected_code: HTTPStatus,
    current_request_with_host: None,
    side_effect: Exception,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test webhook callback."""

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_client_no_auth()
    webhook_url = async_generate_url(hass, WEBHOOK_ID)
    mock_tedee.parse_webhook_message.side_effect = side_effect
    resp = await client.post(urlparse(webhook_url).path, json=body)

    # Wait for remaining tasks to complete.
    await hass.async_block_till_done()

    assert resp.status == expected_code
