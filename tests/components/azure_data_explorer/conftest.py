"""Test fixtures for ADX."""
from datetime import timedelta
import logging
from unittest.mock import patch

import pytest

from homeassistant.components.azure_data_explorer.const import (
    CONF_FILTER,
    CONF_SEND_INTERVAL,
    DOMAIN,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_ON
from homeassistant.setup import async_setup_component
from homeassistant.util.dt import utcnow

from .const import AZURE_DATA_EXPLORER_PATH, BASE_CONFIG, BASIC_OPTIONS, CLIENT_PATH

from tests.common import MockConfigEntry, async_fire_time_changed

_LOGGER = logging.getLogger(__name__)


# fixtures for both init and config flow tests
@pytest.fixture(autouse=True, name="mock_test_connection")
def mock_test_connection():
    """Mock azure data explorer test_connection, used to test the connection."""
    with patch(f"{CLIENT_PATH}.test_connection") as test_connection:
        yield test_connection


@pytest.fixture(autouse=True, name="mock_ingest_data")
def mock_ingest_data():
    """Mock azure data explorer data ingestion."""
    with patch(f"{CLIENT_PATH}.ingest_data") as ingest_data:
        yield ingest_data


@pytest.fixture(name="filter_schema")
def mock_filter_schema():
    """Return an empty filter."""
    return {}


@pytest.fixture(name="entry")
async def mock_entry_fixture(hass, filter_schema):
    """Create the setup in HA."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=BASE_CONFIG,
        title="test-instance",
        options=BASIC_OPTIONS,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(
        hass, DOMAIN, {DOMAIN: {CONF_FILTER: filter_schema}}
    )
    assert entry.state == ConfigEntryState.LOADED

    # Clear the component_loaded event from the queue.
    async_fire_time_changed(
        hass,
        utcnow() + timedelta(seconds=entry.options[CONF_SEND_INTERVAL]),
    )
    await hass.async_block_till_done()
    return entry


# fixtures for init tests
@pytest.fixture(name="entry_with_one_event")
async def mock_entry_with_one_event(hass, entry):
    """Use the entry and add a single test event to the queue."""
    assert entry.state == ConfigEntryState.LOADED
    hass.states.async_set("sensor.test", STATE_ON)
    return entry


@pytest.fixture(name="mock_setup_entry")
def mock_setup_entry():
    """Mock the setup entry call, used for config flow tests."""
    with patch(
        f"{AZURE_DATA_EXPLORER_PATH}.async_setup_entry", return_value=True
    ) as setup_entry:
        yield setup_entry
