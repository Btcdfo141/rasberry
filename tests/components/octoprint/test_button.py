"""Test the OctoPrint buttons."""
from unittest.mock import patch

from pyoctoprintapi import OctoprintPrinterInfo
import pytest

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.components.octoprint import OctoprintDataUpdateCoordinator
from homeassistant.components.octoprint.button import InvalidPrinterState
from homeassistant.components.octoprint.const import DOMAIN
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_registry import async_get

from . import init_integration


@callback
def _enable_entity(hass: HomeAssistant, entity_id: str) -> None:
    """Enable disabled entity."""
    ent_reg = async_get(hass)
    entry = ent_reg.async_get(entity_id)
    updated_entry = ent_reg.async_update_entity(
        entry.entity_id, **{"disabled_by": None}
    )
    assert updated_entry != entry
    assert updated_entry.disabled is False


async def test_pause_job(hass: HomeAssistant) -> None:
    """Test the pause job button."""
    await init_integration(hass, BUTTON_DOMAIN)

    coordinator: OctoprintDataUpdateCoordinator = hass.data[DOMAIN]["uuid"][
        "coordinator"
    ]

    # Test pausing the printer when it is printing
    with patch("pyoctoprintapi.OctoprintClient.pause_job") as pause_command:
        coordinator.data["printer"] = OctoprintPrinterInfo(
            {"state": {"flags": {"printing": True}}, "temperature": []}
        )
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.octoprint_pause_job",
            },
            blocking=True,
        )

        assert len(pause_command.mock_calls) == 1

    # Test pausing the printer when it is paused
    with patch("pyoctoprintapi.OctoprintClient.pause_job") as pause_command:
        coordinator.data["printer"] = OctoprintPrinterInfo(
            {"state": {"flags": {"printing": False, "paused": True}}, "temperature": []}
        )
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.octoprint_pause_job",
            },
            blocking=True,
        )

        assert len(pause_command.mock_calls) == 0

    # Test pausing the printer when it is stopped
    with patch(
        "pyoctoprintapi.OctoprintClient.pause_job"
    ) as pause_command, pytest.raises(InvalidPrinterState):
        coordinator.data["printer"] = OctoprintPrinterInfo(
            {
                "state": {"flags": {"printing": False, "paused": False}},
                "temperature": [],
            }
        )
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.octoprint_pause_job",
            },
            blocking=True,
        )


async def test_resume_job(hass: HomeAssistant) -> None:
    """Test the resume job button."""
    await init_integration(hass, BUTTON_DOMAIN)

    coordinator: OctoprintDataUpdateCoordinator = hass.data[DOMAIN]["uuid"][
        "coordinator"
    ]

    # Test resuming the printer when it is paused
    with patch("pyoctoprintapi.OctoprintClient.resume_job") as resume_command:
        coordinator.data["printer"] = OctoprintPrinterInfo(
            {"state": {"flags": {"printing": False, "paused": True}}, "temperature": []}
        )
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.octoprint_resume_job",
            },
            blocking=True,
        )

        assert len(resume_command.mock_calls) == 1

    # Test resuming the printer when it is printing
    with patch("pyoctoprintapi.OctoprintClient.resume_job") as resume_command:
        coordinator.data["printer"] = OctoprintPrinterInfo(
            {"state": {"flags": {"printing": True, "paused": False}}, "temperature": []}
        )
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.octoprint_resume_job",
            },
            blocking=True,
        )

        assert len(resume_command.mock_calls) == 0

    # Test resuming the printer when it is stopped
    with patch(
        "pyoctoprintapi.OctoprintClient.resume_job"
    ) as resume_command, pytest.raises(InvalidPrinterState):
        coordinator.data["printer"] = OctoprintPrinterInfo(
            {
                "state": {"flags": {"printing": False, "paused": False}},
                "temperature": [],
            }
        )
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.octoprint_resume_job",
            },
            blocking=True,
        )


async def test_stop_job(hass: HomeAssistant) -> None:
    """Test the stop job button."""
    await init_integration(hass, BUTTON_DOMAIN)

    coordinator: OctoprintDataUpdateCoordinator = hass.data[DOMAIN]["uuid"][
        "coordinator"
    ]

    # Test stopping the printer when it is paused
    with patch("pyoctoprintapi.OctoprintClient.cancel_job") as stop_command:
        coordinator.data["printer"] = OctoprintPrinterInfo(
            {"state": {"flags": {"printing": False, "paused": True}}, "temperature": []}
        )
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.octoprint_stop_job",
            },
            blocking=True,
        )

        assert len(stop_command.mock_calls) == 1

    # Test stopping the printer when it is printing
    with patch("pyoctoprintapi.OctoprintClient.cancel_job") as stop_command:
        coordinator.data["printer"] = OctoprintPrinterInfo(
            {"state": {"flags": {"printing": True, "paused": False}}, "temperature": []}
        )
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.octoprint_stop_job",
            },
            blocking=True,
        )

        assert len(stop_command.mock_calls) == 1

    # Test stopping the printer when it is stopped
    with patch("pyoctoprintapi.OctoprintClient.cancel_job") as stop_command:
        coordinator.data["printer"] = OctoprintPrinterInfo(
            {
                "state": {"flags": {"printing": False, "paused": False}},
                "temperature": [],
            }
        )
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.octoprint_stop_job",
            },
            blocking=True,
        )

        assert len(stop_command.mock_calls) == 0


async def test_shutdown_system(hass: HomeAssistant) -> None:
    """Test the shutdown system button."""
    await init_integration(hass, BUTTON_DOMAIN)

    coordinator: OctoprintDataUpdateCoordinator = hass.data[DOMAIN]["uuid"][
        "coordinator"
    ]

    # Test shutting down the system
    with patch("pyoctoprintapi.OctoprintClient.shutdown") as shutdown_command:
        coordinator.data["printer"] = OctoprintPrinterInfo(
            {"state": {"flags": {}}, "temperature": []}
        )
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.octoprint_shutdown_system",
            },
            blocking=True,
        )

        assert len(shutdown_command.mock_calls) == 1


async def test_reboot_system(hass: HomeAssistant) -> None:
    """Test the reboot system button."""
    await init_integration(hass, BUTTON_DOMAIN)

    coordinator: OctoprintDataUpdateCoordinator = hass.data[DOMAIN]["uuid"][
        "coordinator"
    ]

    # Test rebooting the system
    with patch("pyoctoprintapi.OctoprintClient.reboot_system") as reboot_command:
        coordinator.data["printer"] = OctoprintPrinterInfo(
            {"state": {"flags": {}}, "temperature": []}
        )
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.octoprint_reboot_system",
            },
            blocking=True,
        )

        assert len(reboot_command.mock_calls) == 1


async def test_restart_octoprint(hass: HomeAssistant) -> None:
    """Test the restart octoprint button."""
    await init_integration(hass, BUTTON_DOMAIN)

    coordinator: OctoprintDataUpdateCoordinator = hass.data[DOMAIN]["uuid"][
        "coordinator"
    ]

    # Test restarting octoprint
    with patch("pyoctoprintapi.OctoprintClient.restart") as restart_command:
        coordinator.data["printer"] = OctoprintPrinterInfo(
            {"state": {"flags": {}}, "temperature": []}
        )
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.octoprint_restart_octoprint",
            },
            blocking=True,
        )

        assert len(restart_command.mock_calls) == 1
