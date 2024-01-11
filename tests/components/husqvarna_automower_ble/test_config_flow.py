"""Test the Husqvarna Bluetooth config flow."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant import config_entries
from homeassistant.components.husqvarna_automower_ble.const import DOMAIN
from homeassistant.core import HomeAssistant

from . import (
    AUTOMOWER_MISSING_SERVICE_SERVICE_INFO,
    AUTOMOWER_SERVICE_INFO,
    AUTOMOWER_UNNAMED_SERVICE_INFO,
    AUTOMOWER_UNSUPPORTED_GROUP_SERVICE_INFO,
)
from .conftest import MockMower

from tests.components.bluetooth import inject_bluetooth_service_info

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


@pytest.fixture(name="automower_setup", autouse=True)
def automower_setup_fixture():
    """Mock hue entry setup."""
    with patch(
        "homeassistant.components.husqvarna_automower_ble.config_flow.Mower", MockMower
    ):
        yield


async def test_user_selection(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
) -> None:
    """Test we can select a device."""

    inject_bluetooth_service_info(hass, AUTOMOWER_SERVICE_INFO)
    inject_bluetooth_service_info(hass, AUTOMOWER_UNNAMED_SERVICE_INFO)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result == snapshot

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"address": "00000000-0000-0000-0000-000000000001"},
    )
    assert result == snapshot

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )


async def test_no_devices(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
) -> None:
    """Test missing device."""

    inject_bluetooth_service_info(hass, AUTOMOWER_MISSING_SERVICE_SERVICE_INFO)
    inject_bluetooth_service_info(hass, AUTOMOWER_UNSUPPORTED_GROUP_SERVICE_INFO)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result == snapshot


async def test_bluetooth(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
) -> None:
    """Test bluetooth device discovery."""

    inject_bluetooth_service_info(hass, AUTOMOWER_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = next(iter(hass.config_entries.flow.async_progress_by_handler(DOMAIN)))
    assert result == snapshot

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )


async def test_bluetooth_invalid(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
) -> None:
    """Test bluetooth device discovery with invalid data."""

    inject_bluetooth_service_info(hass, AUTOMOWER_UNSUPPORTED_GROUP_SERVICE_INFO)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=AUTOMOWER_UNSUPPORTED_GROUP_SERVICE_INFO,
    )
    assert result == snapshot
