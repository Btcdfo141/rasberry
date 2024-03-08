"""Tests for the seventeentrack sensor."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from py17track.errors import SeventeenTrackError
from py17track.package import Package

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .conftest import (
    DEFAULT_SUMMARY,
    INVALID_CONFIG,
    NEW_SUMMARY_DATA,
    VALID_CONFIG_FULL,
    VALID_CONFIG_FULL_NO_DELIVERED,
    VALID_CONFIG_MINIMAL,
    _goto_future,
)


async def test_full_valid_config(
    hass: HomeAssistant, mock_seventeentrack: AsyncMock
) -> None:
    """Ensure everything starts correctly."""
    assert await async_setup_component(hass, "sensor", VALID_CONFIG_MINIMAL)
    await hass.async_block_till_done()
    assert len(hass.states.async_entity_ids()) == len(DEFAULT_SUMMARY.keys())


async def test_valid_config(
    hass: HomeAssistant, mock_seventeentrack: AsyncMock
) -> None:
    """Ensure everything starts correctly."""
    assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL)
    await hass.async_block_till_done()
    assert len(hass.states.async_entity_ids()) == len(DEFAULT_SUMMARY.keys())


async def test_invalid_config(hass: HomeAssistant) -> None:
    """Ensure nothing is created when config is wrong."""
    assert await async_setup_component(hass, "sensor", INVALID_CONFIG)
    await hass.async_block_till_done()
    assert not hass.states.async_entity_ids("sensor")


async def test_login_exception(
    hass: HomeAssistant, mock_seventeentrack: AsyncMock
) -> None:
    """Ensure everything starts correctly."""
    mock_seventeentrack.return_value.profile.login.side_effect = SeventeenTrackError(
        "Error"
    )
    assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL)
    await hass.async_block_till_done()
    assert not hass.states.async_entity_ids("sensor")


async def test_add_package(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, mock_seventeentrack: AsyncMock
) -> None:
    """Ensure package is added correctly when user add a new package."""
    package = Package(
        tracking_number="456",
        destination_country=206,
        friendly_name="friendly name 1",
        info_text="info text 1",
        location="location 1",
        timestamp="2020-08-10 10:32",
        origin_country=206,
        package_type=2,
    )
    mock_seventeentrack.return_value.profile.packages.return_value = [package]
    mock_seventeentrack.return_value.profile.summary.return_value = {}

    assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.seventeentrack_package_456") is not None
    assert len(hass.states.async_entity_ids()) == 1

    package2 = Package(
        tracking_number="789",
        destination_country=206,
        friendly_name="friendly name 2",
        info_text="info text 2",
        location="location 2",
        timestamp="2020-08-10 14:25",
        origin_country=206,
        package_type=2,
    )
    mock_seventeentrack.return_value.profile.packages.return_value = [package, package2]

    await _goto_future(hass, freezer)

    assert hass.states.get("sensor.seventeentrack_package_789") is not None
    assert len(hass.states.async_entity_ids()) == 2


async def test_add_package_no_friendly_name(
    hass: HomeAssistant, mock_seventeentrack: AsyncMock
) -> None:
    """Ensure package is added correctly when user add a new package."""
    package = Package(
        tracking_number="456",
        destination_country=206,
        info_text="info text 1",
        location="location 1",
        timestamp="2020-08-10 10:32",
        origin_country=206,
        package_type=2,
    )
    mock_seventeentrack.return_value.profile.packages.return_value = [package]
    mock_seventeentrack.return_value.profile.summary.return_value = {}

    assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL)
    await hass.async_block_till_done()
    state_456 = hass.states.get("sensor.seventeentrack_package_456")
    assert state_456 is not None
    assert state_456.attributes["friendly_name"] == "Seventeentrack Package: 456"
    assert len(hass.states.async_entity_ids()) == 1


async def test_remove_package(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, mock_seventeentrack: AsyncMock
) -> None:
    """Ensure entity is not there anymore if package is not there."""
    package1 = Package(
        tracking_number="456",
        destination_country=206,
        friendly_name="friendly name 1",
        info_text="info text 1",
        location="location 1",
        timestamp="2020-08-10 10:32",
        origin_country=206,
        package_type=2,
    )
    package2 = Package(
        tracking_number="789",
        destination_country=206,
        friendly_name="friendly name 2",
        info_text="info text 2",
        location="location 2",
        timestamp="2020-08-10 14:25",
        origin_country=206,
        package_type=2,
    )

    mock_seventeentrack.return_value.profile.packages.return_value = [
        package1,
        package2,
    ]
    mock_seventeentrack.return_value.profile.summary.return_value = {}

    assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.seventeentrack_package_456") is not None
    assert hass.states.get("sensor.seventeentrack_package_789") is not None
    assert len(hass.states.async_entity_ids()) == 2

    mock_seventeentrack.return_value.profile.packages.return_value = [package2]

    await _goto_future(hass, freezer)

    assert hass.states.get("sensor.seventeentrack_package_456") is None
    assert hass.states.get("sensor.seventeentrack_package_789") is not None
    assert len(hass.states.async_entity_ids()) == 1


async def test_package_error(
    hass: HomeAssistant, mock_seventeentrack: AsyncMock
) -> None:
    """Ensure package is added correctly when user add a new package."""
    mock_seventeentrack.return_value.profile.packages.side_effect = SeventeenTrackError(
        "Error"
    )
    mock_seventeentrack.return_value.profile.summary.return_value = {}

    assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.seventeentrack_package_456") is None


async def test_friendly_name_changed(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, mock_seventeentrack: AsyncMock
) -> None:
    """Test friendly name change."""
    package = Package(
        tracking_number="456",
        destination_country=206,
        friendly_name="friendly name 1",
        info_text="info text 1",
        location="location 1",
        timestamp="2020-08-10 10:32",
        origin_country=206,
        package_type=2,
    )
    mock_seventeentrack.return_value.profile.packages.return_value = [package]
    mock_seventeentrack.return_value.profile.summary.return_value = {}

    assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.seventeentrack_package_456") is not None
    assert len(hass.states.async_entity_ids()) == 1

    package = Package(
        tracking_number="456",
        destination_country=206,
        friendly_name="friendly name 2",
        info_text="info text 1",
        location="location 1",
        timestamp="2020-08-10 10:32",
        origin_country=206,
        package_type=2,
    )
    mock_seventeentrack.return_value.profile.packages.return_value = [package]

    await _goto_future(hass, freezer)

    assert hass.states.get("sensor.seventeentrack_package_456") is not None
    entity = hass.data["entity_components"]["sensor"].get_entity(
        "sensor.seventeentrack_package_456"
    )
    assert entity.name == "Seventeentrack Package: friendly name 2"
    assert len(hass.states.async_entity_ids()) == 1


async def test_delivered_not_shown(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, mock_seventeentrack: AsyncMock
) -> None:
    """Ensure delivered packages are not shown."""
    package = Package(
        tracking_number="456",
        destination_country=206,
        friendly_name="friendly name 1",
        info_text="info text 1",
        location="location 1",
        timestamp="2020-08-10 10:32",
        origin_country=206,
        package_type=2,
        status=40,
    )
    mock_seventeentrack.return_value.profile.packages.return_value = [package]
    mock_seventeentrack.return_value.profile.summary.return_value = {}

    with patch(
        "homeassistant.components.seventeentrack.sensor.persistent_notification"
    ) as persistent_notification_mock:
        assert await async_setup_component(
            hass, "sensor", VALID_CONFIG_FULL_NO_DELIVERED
        )
        await hass.async_block_till_done()
        await _goto_future(hass, freezer)

        assert not hass.states.async_entity_ids()
        persistent_notification_mock.create.assert_called()


async def test_delivered_shown(
    hass: HomeAssistant, mock_seventeentrack: AsyncMock
) -> None:
    """Ensure delivered packages are show when user choose to show them."""
    package = Package(
        tracking_number="456",
        destination_country=206,
        friendly_name="friendly name 1",
        info_text="info text 1",
        location="location 1",
        timestamp="2020-08-10 10:32",
        origin_country=206,
        package_type=2,
        status=40,
    )
    mock_seventeentrack.return_value.profile.packages.return_value = [package]
    mock_seventeentrack.return_value.profile.summary.return_value = {}

    with patch(
        "homeassistant.components.seventeentrack.sensor.persistent_notification"
    ) as persistent_notification_mock:
        assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL)
        await hass.async_block_till_done()

        assert hass.states.get("sensor.seventeentrack_package_456") is not None
        assert len(hass.states.async_entity_ids()) == 1
        persistent_notification_mock.create.assert_not_called()


async def test_becomes_delivered_not_shown_notification(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, mock_seventeentrack: AsyncMock
) -> None:
    """Ensure notification is triggered when package becomes delivered."""
    package = Package(
        tracking_number="456",
        destination_country=206,
        friendly_name="friendly name 1",
        info_text="info text 1",
        location="location 1",
        timestamp="2020-08-10 10:32",
        origin_country=206,
        package_type=2,
    )
    mock_seventeentrack.return_value.profile.packages.return_value = [package]
    mock_seventeentrack.return_value.profile.summary.return_value = {}

    assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL_NO_DELIVERED)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.seventeentrack_package_456") is not None
    assert len(hass.states.async_entity_ids()) == 1

    package_delivered = Package(
        tracking_number="456",
        destination_country=206,
        friendly_name="friendly name 1",
        info_text="info text 1",
        location="location 1",
        timestamp="2020-08-10 10:32",
        origin_country=206,
        package_type=2,
        status=40,
    )
    mock_seventeentrack.return_value.profile.packages.return_value = [package_delivered]

    with patch(
        "homeassistant.components.seventeentrack.sensor.persistent_notification"
    ) as persistent_notification_mock:
        await _goto_future(hass, freezer)

        persistent_notification_mock.create.assert_called()
        assert not hass.states.async_entity_ids()


async def test_summary_correctly_updated(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, mock_seventeentrack: AsyncMock
) -> None:
    """Ensure summary entities are not duplicated."""
    package = Package(
        tracking_number="456",
        destination_country=206,
        friendly_name="friendly name 1",
        info_text="info text 1",
        location="location 1",
        timestamp="2020-08-10 10:32",
        origin_country=206,
        package_type=2,
        status=30,
    )
    mock_seventeentrack.return_value.profile.packages.return_value = [package]
    mock_seventeentrack.return_value.profile.summary.return_value = DEFAULT_SUMMARY

    assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL)
    await hass.async_block_till_done()

    assert len(hass.states.async_entity_ids()) == 8
    for state in hass.states.async_all():
        if state.entity_id == "sensor.seventeentrack_package_456":
            break
        assert state.state == "0"

    state_ready_picked = hass.states.get(
        "sensor.seventeentrack_packages_ready_to_be_picked_up"
    )
    assert state_ready_picked is not None
    assert len(state_ready_picked.attributes["packages"]) == 1

    mock_seventeentrack.return_value.profile.packages.return_value = []
    mock_seventeentrack.return_value.profile.summary.return_value = NEW_SUMMARY_DATA

    await _goto_future(hass, freezer)

    assert len(hass.states.async_entity_ids()) == 7
    for state in hass.states.async_all():
        assert state.state == "1"

    state_ready_picked = hass.states.get(
        "sensor.seventeentrack_packages_ready_to_be_picked_up"
    )
    assert state_ready_picked is not None
    assert state_ready_picked.attributes["packages"] is None


async def test_summary_error(
    hass: HomeAssistant, mock_seventeentrack: AsyncMock
) -> None:
    """Test summary empty if error."""
    package = Package(
        tracking_number="456",
        destination_country=206,
        friendly_name="friendly name 1",
        info_text="info text 1",
        location="location 1",
        timestamp="2020-08-10 10:32",
        origin_country=206,
        package_type=2,
        status=30,
    )
    mock_seventeentrack.return_value.profile.packages.return_value = [package]
    mock_seventeentrack.return_value.profile.summary.side_effect = SeventeenTrackError(
        "Error"
    )

    assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL)
    await hass.async_block_till_done()

    assert len(hass.states.async_entity_ids()) == 1
    for state in hass.states.async_all():
        if state.entity_id == "sensor.seventeentrack_package_456":
            break
        assert state.state == "0"

    assert (
        hass.states.get("sensor.seventeentrack_packages_ready_to_be_picked_up") is None
    )


async def test_utc_timestamp(
    hass: HomeAssistant, mock_seventeentrack: AsyncMock
) -> None:
    """Ensure package timestamp is converted correctly from HA-defined time zone to UTC."""
    package = Package(
        tracking_number="456",
        destination_country=206,
        friendly_name="friendly name 1",
        info_text="info text 1",
        location="location 1",
        timestamp="2020-08-10 10:32",
        origin_country=206,
        package_type=2,
        tz="Asia/Jakarta",
    )
    mock_seventeentrack.return_value.profile.packages.return_value = [package]
    mock_seventeentrack.return_value.profile.summary.return_value = {}

    assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.seventeentrack_package_456") is not None
    assert len(hass.states.async_entity_ids()) == 1
    state_456 = hass.states.get("sensor.seventeentrack_package_456")
    assert state_456 is not None
    assert str(state_456.attributes.get("timestamp")) == "2020-08-10 03:32:00+00:00"


async def test_non_valid_platform_config(
    hass: HomeAssistant, mock_seventeentrack: AsyncMock
) -> None:
    """Test if login fails."""
    mock_seventeentrack.return_value.profile.login.return_value = False
    assert await async_setup_component(hass, "sensor", VALID_CONFIG_FULL)
    await hass.async_block_till_done()
    assert len(hass.states.async_entity_ids()) == 0
