"""The tests for the Ring component."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest
from ring_doorbell import AuthenticationError, RingError, RingTimeout

import homeassistant.components.ring as ring
from homeassistant.components.ring import DOMAIN
from homeassistant.components.ring.const import SCAN_INTERVAL
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.issue_registry import IssueRegistry
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_setup(hass: HomeAssistant, mock_ring_client) -> None:
    """Test the setup."""
    await async_setup_component(hass, ring.DOMAIN, {})


async def test_setup_entry(
    hass: HomeAssistant,
    mock_ring_client,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup entry."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_setup_entry_device_update(
    hass: HomeAssistant,
    mock_ring_client,
    mock_ring_devices,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test devices are updating after setup entry."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    front_door_doorbell = mock_ring_devices["doorbots"][987654]
    front_door_doorbell.history.assert_not_called()
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass, dt_util.now() + timedelta(minutes=20))
    await hass.async_block_till_done(wait_background_tasks=True)
    front_door_doorbell.history.assert_called_once()


async def test_auth_failed_on_setup(
    hass: HomeAssistant,
    mock_ring_client,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test auth failure on setup entry."""
    mock_config_entry.add_to_hass(hass)
    mock_ring_client.update_data.side_effect = AuthenticationError

    assert not any(mock_config_entry.async_get_active_flows(hass, {SOURCE_REAUTH}))
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert any(mock_config_entry.async_get_active_flows(hass, {SOURCE_REAUTH}))
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


@pytest.mark.parametrize(
    ("error_type", "log_msg"),
    [
        (
            RingTimeout,
            "Timeout communicating with API: ",
        ),
        (
            RingError,
            "Error communicating with API: ",
        ),
    ],
    ids=["timeout-error", "other-error"],
)
async def test_error_on_setup(
    hass: HomeAssistant,
    mock_ring_client,
    mock_config_entry: MockConfigEntry,
    caplog,
    error_type,
    log_msg,
) -> None:
    """Test non-auth errors on setup entry."""
    mock_config_entry.add_to_hass(hass)

    mock_ring_client.update_data.side_effect = error_type

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY

    assert [
        record.message
        for record in caplog.records
        if record.levelname == "DEBUG"
        and record.name == "homeassistant.config_entries"
        and log_msg in record.message
        and DOMAIN in record.message
    ]


async def test_auth_failure_on_global_update(
    hass: HomeAssistant,
    mock_ring_client,
    mock_config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test authentication failure on global data update."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert not any(mock_config_entry.async_get_active_flows(hass, {SOURCE_REAUTH}))

    mock_ring_client.update_devices.side_effect = AuthenticationError

    async_fire_time_changed(hass, dt_util.now() + timedelta(minutes=20))
    await hass.async_block_till_done()

    assert "Authentication failed while fetching devices data: " in [
        record.message
        for record in caplog.records
        if record.levelname == "ERROR"
        and record.name == "homeassistant.components.ring.coordinator"
    ]

    assert any(mock_config_entry.async_get_active_flows(hass, {SOURCE_REAUTH}))


async def test_auth_failure_on_device_update(
    hass: HomeAssistant,
    mock_ring_client,
    mock_ring_devices,
    mock_config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test authentication failure on device data update."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert not any(mock_config_entry.async_get_active_flows(hass, {SOURCE_REAUTH}))

    front_door_doorbell = mock_ring_devices["doorbots"][987654]
    front_door_doorbell.history.side_effect = AuthenticationError

    async_fire_time_changed(hass, dt_util.now() + timedelta(minutes=20))
    await hass.async_block_till_done(wait_background_tasks=True)

    assert "Authentication failed while fetching devices data: " in [
        record.message
        for record in caplog.records
        if record.levelname == "ERROR"
        and record.name == "homeassistant.components.ring.coordinator"
    ]

    assert any(mock_config_entry.async_get_active_flows(hass, {SOURCE_REAUTH}))


@pytest.mark.parametrize(
    ("error_type", "log_msg"),
    [
        (
            RingTimeout,
            "Error fetching devices data: Timeout communicating with API: ",
        ),
        (
            RingError,
            "Error fetching devices data: Error communicating with API: ",
        ),
    ],
    ids=["timeout-error", "other-error"],
)
async def test_error_on_global_update(
    hass: HomeAssistant,
    mock_ring_client,
    mock_config_entry: MockConfigEntry,
    caplog,
    error_type,
    log_msg,
) -> None:
    """Test non-auth errors on global data update."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    mock_ring_client.update_devices.side_effect = error_type

    async_fire_time_changed(hass, dt_util.now() + timedelta(minutes=20))
    await hass.async_block_till_done(wait_background_tasks=True)

    assert log_msg in [
        record.message for record in caplog.records if record.levelname == "ERROR"
    ]

    assert mock_config_entry.entry_id in hass.data[DOMAIN]


@pytest.mark.parametrize(
    ("error_type", "log_msg"),
    [
        (
            RingTimeout,
            "Error fetching devices data: Timeout communicating with API for device Front: ",
        ),
        (
            RingError,
            "Error fetching devices data: Error communicating with API for device Front: ",
        ),
    ],
    ids=["timeout-error", "other-error"],
)
async def test_error_on_device_update(
    hass: HomeAssistant,
    mock_ring_client,
    mock_ring_devices,
    mock_config_entry: MockConfigEntry,
    caplog,
    error_type,
    log_msg,
) -> None:
    """Test non-auth errors on device update."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    front_door_doorbell = mock_ring_devices["stickup_cams"][765432]
    front_door_doorbell.history.side_effect = error_type

    async_fire_time_changed(hass, dt_util.now() + timedelta(minutes=20))
    await hass.async_block_till_done(wait_background_tasks=True)

    assert log_msg in [
        record.message for record in caplog.records if record.levelname == "ERROR"
    ]
    assert mock_config_entry.entry_id in hass.data[DOMAIN]


async def test_issue_deprecated_service_ring_update(
    hass: HomeAssistant,
    issue_registry: IssueRegistry,
    caplog: pytest.LogCaptureFixture,
    mock_ring_client,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the issue is raised on deprecated service ring.update."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    _ = await hass.services.async_call(DOMAIN, "update", {}, blocking=True)

    issue = issue_registry.async_get_issue("ring", "deprecated_service_ring_update")
    assert issue
    assert issue.issue_domain == "ring"
    assert issue.issue_id == "deprecated_service_ring_update"
    assert issue.translation_key == "deprecated_service_ring_update"

    assert (
        "Detected use of service 'ring.update'. "
        "This is deprecated and will stop working in Home Assistant 2024.10. "
        "Use 'homeassistant.update_entity' instead which updates all ring entities"
    ) in caplog.text
