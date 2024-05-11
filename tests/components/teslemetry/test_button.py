"""Test the Teslemetry button platform."""

from unittest.mock import patch

import pytest
from syrupy import SnapshotAssertion

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import assert_entities, setup_platform
from .const import COMMAND_OK


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_button(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Tests that the climate entity is correct."""

    entry = await setup_platform(hass, [Platform.BUTTON])
    assert_entities(hass, entry.entry_id, entity_registry, snapshot, False)


@pytest.mark.parametrize(
    ("name", "func"),
    [
        ("flash_lights", "flash_lights"),
        ("honk_horn", "honk_horn"),
        ("keyless_driving", "remote_start_drive"),
        ("play_fart", "remote_boombox"),
        ("homelink", "trigger_homelink"),
    ],
)
async def test_press(hass: HomeAssistant, name: str, func: str) -> None:
    """Test pressing all the buttons."""
    await setup_platform(hass, [Platform.BUTTON])

    with patch(
        f"homeassistant.components.teslemetry.VehicleSpecific.{func}",
        return_value=COMMAND_OK,
    ) as command:
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [f"button.test_{name}"]},
            blocking=True,
        )
        command.assert_called_once()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_refresh(hass: HomeAssistant) -> None:
    """Test pressing the refresh button."""
    await setup_platform(hass, [Platform.BUTTON])

    with patch(
        "homeassistant.components.teslemetry.TeslemetryVehicleDataCoordinator.async_request_refresh"
    ) as command:
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: ["button.test_force_refresh"]},
            blocking=True,
        )
        command.assert_called_once()
