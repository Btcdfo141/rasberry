"""Test init of LCN integration."""
import json
from unittest.mock import patch

from pypck.connection import (
    PchkAuthenticationError,
    PchkConnectionManager,
    PchkLicenseError,
)
import pytest

from homeassistant import config_entries
import homeassistant.components.lcn
from homeassistant.components.lcn.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .conftest import (
    CONNECTION_DATA,
    DATA,
    OPTIONS,
    MockPchkConnectionManager,
    setup_component,
)

from tests.common import MockConfigEntry, load_fixture


async def test_async_setup_entry(hass, entry, lcn_connection):
    """Test a successful setup entry and unload of entry."""
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state == ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.NOT_LOADED
    assert not hass.data.get(DOMAIN)


async def test_async_setup_existing_entry(hass, entry, lcn_connection):
    """Test setup of an existing entry."""
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state == ConfigEntryState.LOADED

    result = await homeassistant.components.lcn.async_setup_entry(hass, entry)
    assert not result

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state == ConfigEntryState.LOADED


async def test_async_setup_multiple_entries(hass, entry, entry2):
    """Test a successful setup and unload of multiple entries."""
    with patch("pypck.connection.PchkConnectionManager", MockPchkConnectionManager):
        for config_entry in (entry, entry2):
            config_entry.add_to_hass(hass)
            await hass.config_entries.async_setup(config_entry.entry_id)
            await hass.async_block_till_done()
            assert config_entry.state == ConfigEntryState.LOADED

    assert len(hass.config_entries.async_entries(DOMAIN)) == 2

    for config_entry in (entry, entry2):
        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

        assert config_entry.state == ConfigEntryState.NOT_LOADED

    assert not hass.data.get(DOMAIN)


async def test_async_setup_entry_update(hass, entry):
    """Test a successful setup entry if entry with same id already exists."""
    # setup first entry
    entry.source = config_entries.SOURCE_IMPORT
    entry.add_to_hass(hass)

    # create dummy entity for LCN platform as an orphan
    entity_registry = er.async_get(hass)
    dummy_entity = entity_registry.async_get_or_create(
        "switch", DOMAIN, "dummy", config_entry=entry
    )

    # create dummy device for LCN platform as an orphan
    device_registry = dr.async_get(hass)
    dummy_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id, 0, 7, False)},
        via_device=(DOMAIN, entry.entry_id),
    )

    assert dummy_entity in entity_registry.entities.values()
    assert dummy_device in device_registry.devices.values()

    # setup new entry with same data via import step (should cleanup dummy device)
    fixture_filename = "lcn/config_entry_pchk.json"
    config_data = json.loads(load_fixture(fixture_filename))
    with patch("pypck.connection.PchkConnectionManager", MockPchkConnectionManager):
        await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=config_data
        )

    assert dummy_device not in device_registry.devices.values()
    assert dummy_entity not in entity_registry.entities.values()


@pytest.mark.parametrize(
    "error",
    [
        PchkAuthenticationError,
        PchkLicenseError,
        TimeoutError,
        ConnectionRefusedError,
    ],
)
async def test_async_setup_entry_raises_error(hass, entry, error):
    """Test that an authentication error is handled properly."""
    with patch.object(PchkConnectionManager, "async_connect", side_effect=error):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.SETUP_ERROR


async def test_async_setup_from_configuration_yaml(hass):
    """Test a successful setup using data from configuration.yaml."""
    with patch(
        "pypck.connection.PchkConnectionManager", MockPchkConnectionManager
    ), patch("homeassistant.components.lcn.async_setup_entry") as async_setup_entry:
        await setup_component(hass)

        assert async_setup_entry.await_count == 2


async def test_migrate_entry(hass):
    """Test successful migration of entry data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=CONNECTION_DATA[CONF_HOST],
        unique_id="test",
        data=CONNECTION_DATA,
    )

    assert entry.unique_id == "test"
    assert entry.version == 1
    assert entry.data == CONNECTION_DATA

    await entry.async_migrate(hass)

    assert entry.unique_id == "test"
    assert entry.version == 2
    assert entry.data == {CONF_HOST: "pchk"} | DATA
    assert entry.options == OPTIONS
