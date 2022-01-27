"""Test honeywell setup process."""

from unittest.mock import create_autospec, patch

import somecomfort

from homeassistant.components.honeywell.const import (
    CONF_COOL_AWAY_TEMPERATURE,
    CONF_HEAT_AWAY_TEMPERATURE,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EntityRegistry

from tests.common import MockConfigEntry

MIGRATE_OPTIONS_KEYS = {CONF_COOL_AWAY_TEMPERATURE, CONF_HEAT_AWAY_TEMPERATURE}


@patch("homeassistant.components.honeywell.UPDATE_LOOP_SLEEP_TIME", 0)
async def test_setup_entry(hass: HomeAssistant, config_entry: MockConfigEntry):
    """Initialize the config entry."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.async_entity_ids_count() == 1


@patch("homeassistant.components.honeywell.UPDATE_LOOP_SLEEP_TIME", 0)
async def test_setup_multiple_thermostats(
    hass: HomeAssistant, config_entry: MockConfigEntry, location, another_device
) -> None:
    """Test that the config form is shown."""
    location.devices_by_id[another_device.deviceid] = another_device
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.async_entity_ids_count() == 2


@patch("homeassistant.components.honeywell.UPDATE_LOOP_SLEEP_TIME", 0)
async def test_setup_multiple_thermostats_with_same_deviceid(
    hass: HomeAssistant, caplog, config_entry: MockConfigEntry, device, client
) -> None:
    """Test Honeywell TCC API returning duplicate device IDs."""
    mock_location2 = create_autospec(somecomfort.Location, instance=True)
    mock_location2.locationid.return_value = "location2"
    mock_location2.devices_by_id = {device.deviceid: device}
    client.locations_by_id["location2"] = mock_location2
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.async_entity_ids_count() == 1
    assert "Platform honeywell does not generate unique IDs" not in caplog.text


async def test_away_temps_migration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    entity_reg: EntityRegistry,
    client,
    location,
    device,
) -> None:
    """Test away temps migrate to config options."""
    # Create legacy config data
    config_entry.add_to_hass(hass)
    # Run integration setup
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    # Assert away temps are in config options
    # registry = entity_reg.async_get(hass)
    # registry.
    # assert MIGRATE_OPTIONS_KEYS.intersection(entry.options)
