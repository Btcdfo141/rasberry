"""Tests for 1-Wire config flow."""
from collections.abc import Awaitable, Callable
from unittest.mock import MagicMock, patch

import aiohttp
from pyownet import protocol
import pytest

from homeassistant.components.onewire.const import DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component

from . import setup_owproxy_mock_devices


async def remove_device(
    ws_client: aiohttp.ClientWebSocketResponse, device_id: str, config_entry_id: str
) -> bool:
    """Remove config entry from a device."""
    await ws_client.send_json(
        {
            "id": 1,
            "type": "config/device_registry/remove_config_entry",
            "config_entry_id": config_entry_id,
            "device_id": device_id,
        }
    )
    response = await ws_client.receive_json()
    return response["success"]


@pytest.mark.usefixtures("owproxy_with_connerror")
async def test_connect_failure(hass: HomeAssistant, config_entry: ConfigEntry):
    """Test connection failure raises ConfigEntryNotReady."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.data.get(DOMAIN)


async def test_listing_failure(
    hass: HomeAssistant, config_entry: ConfigEntry, owproxy: MagicMock
):
    """Test listing failure raises ConfigEntryNotReady."""
    owproxy.return_value.dir.side_effect = protocol.OwnetError()

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.data.get(DOMAIN)


@pytest.mark.usefixtures("owproxy")
async def test_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Test being able to unload an entry."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert not hass.data.get(DOMAIN)


@patch("homeassistant.components.onewire.PLATFORMS", [Platform.SENSOR])
async def test_registry_cleanup(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    owproxy: MagicMock,
    hass_ws_client: Callable[
        [HomeAssistant], Awaitable[aiohttp.ClientWebSocketResponse]
    ],
):
    """Test being able to remove a disconnected device."""
    assert await async_setup_component(hass, "config", {})

    entry_id = config_entry.entry_id
    device_registry = dr.async_get(hass)

    # Initialise with two components
    setup_owproxy_mock_devices(
        owproxy, Platform.SENSOR, ["10.111111111111", "28.111111111111"]
    )
    await hass.config_entries.async_setup(entry_id)
    await hass.async_block_till_done()

    # Reload with a device no longer on bus
    setup_owproxy_mock_devices(owproxy, Platform.SENSOR, ["10.111111111111"])
    await hass.config_entries.async_reload(entry_id)
    await hass.async_block_till_done()
    assert len(dr.async_entries_for_config_entry(device_registry, entry_id)) == 2

    # Try to remove "10.111111111111" - fails
    identifiers = {(DOMAIN, "10.111111111111")}
    device = device_registry.async_get_device(identifiers=identifiers)
    assert await remove_device(await hass_ws_client(hass), device.id, entry_id) is False
    assert len(dr.async_entries_for_config_entry(device_registry, entry_id)) == 2
    assert device_registry.async_get_device(identifiers=identifiers) is not None

    # Try to remove "28.111111111111" - succeeds
    identifiers = {(DOMAIN, "28.111111111111")}
    device = device_registry.async_get_device(identifiers=identifiers)
    assert await remove_device(await hass_ws_client(hass), device.id, entry_id) is True
    assert len(dr.async_entries_for_config_entry(device_registry, entry_id)) == 1
    assert device_registry.async_get_device(identifiers=identifiers) is None
