"""Support for Home Connect button entities."""
from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import _get_appliance_by_device_id
from .api import HomeConnectDevice
from .const import BSH_PAUSE, BSH_RESUME, DOMAIN

_PAUSE_KEY = "pause"
_RESUME_KEY = "resume"
_STOP_KEY = "stop"


@dataclass
class HomeConnectEntityDescription(ButtonEntityDescription):
    """Class to describe a Home Connect button."""

    remote_function: Callable[[HomeAssistant, str], Coroutine[Any, Any, Any]]


async def async_service_pause_program(hass: HomeAssistant, device_id: str):
    """Service for pausing a program."""
    await async_service_command(hass, device_id, BSH_PAUSE)


async def async_service_resume_program(hass: HomeAssistant, device_id: str):
    """Service for resuming a paused program."""
    await async_service_command(hass, device_id, BSH_RESUME)


async def async_service_stop_program(hass: HomeAssistant, device_id: str):
    """Execute calls to services executing a stop of active program."""

    appliance = _get_appliance_by_device_id(hass, device_id)
    await hass.async_add_executor_job(appliance.stop_program)


async def async_service_command(hass: HomeAssistant, device_id: str, command):
    """Execute calls to services executing a command."""
    appliance = _get_appliance_by_device_id(hass, device_id)
    await hass.async_add_executor_job(appliance.execute_command, command)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeConnect control buttons."""

    hc_api = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[HomeConnectButton] = []

    for device_dict in hc_api.devices:
        entities.append(
            HomeConnectButton(
                device_dict[CONF_DEVICE],
                HomeConnectEntityDescription(
                    key=_PAUSE_KEY,
                    name="Pause",
                    remote_function=async_service_pause_program,
                ),
            )
        )
        entities.append(
            HomeConnectButton(
                device_dict[CONF_DEVICE],
                HomeConnectEntityDescription(
                    key=_RESUME_KEY,
                    name="Resume",
                    remote_function=async_service_resume_program,
                ),
            )
        )
        entities.append(
            HomeConnectButton(
                device_dict[CONF_DEVICE],
                HomeConnectEntityDescription(
                    key=_STOP_KEY,
                    name="Stop",
                    remote_function=async_service_stop_program,
                ),
            )
        )

    async_add_entities(entities, True)


class HomeConnectButton(HomeConnectDevice, ButtonEntity):
    """HomeConnect Button Device."""

    entity_description: HomeConnectEntityDescription
    device: HomeConnectDevice

    def __init__(
        self,
        device: HomeConnectDevice,
        description: HomeConnectEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(device, "Button")
        self.entity_description = description
        self._attr_unique_id = f"{super().unique_id}{description.key}"

    async def async_press(self) -> None:
        """Press the button."""
        await self.entity_description.remote_function(
            self.hass, self.device.appliance.haId
        )
