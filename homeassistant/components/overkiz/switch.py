"""Support for Overkiz switches."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pyoverkiz.enums import OverkizCommand, OverkizCommandParam, OverkizState
from pyoverkiz.enums.ui import UIClass, UIWidget

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomeAssistantOverkizData
from .const import DOMAIN
from .entity import OverkizDescriptiveEntity


@dataclass
class OverkizSwitchDescriptionMixin:
    """Define an entity description mixin for number entities."""

    turn_on: Callable[[Callable], None]
    turn_off: Callable[[Callable], None]
    is_on: Callable[[Callable], bool]


@dataclass
class OverkizSwitchDescription(SwitchEntityDescription, OverkizSwitchDescriptionMixin):
    """Class to describe an Overkiz number."""


SWITCH_DESCRIPTIONS: list[OverkizSwitchDescription] = [
    OverkizSwitchDescription(
        key=UIWidget.DOMESTIC_HOT_WATER_TANK,
        turn_on=lambda execute_command: execute_command(
            OverkizCommand.SET_FORCE_HEATING, OverkizCommandParam.ON
        ),
        turn_off=lambda execute_command: execute_command(
            OverkizCommand.SET_FORCE_HEATING, OverkizCommandParam.OFF
        ),
        is_on=lambda select_state: (
            select_state(OverkizState.IO_FORCE_HEATING) == OverkizCommandParam.ON
        ),
    ),
    OverkizSwitchDescription(
        key=UIClass.ON_OFF,
        turn_on=lambda execute_command: execute_command(OverkizCommand.ON),
        turn_off=lambda execute_command: execute_command(OverkizCommand.OFF),
        is_on=lambda select_state: (
            select_state(OverkizState.CORE_ON_OFF) == OverkizCommandParam.ON
        ),
        device_class=SwitchDeviceClass.OUTLET,
    ),
    OverkizSwitchDescription(
        key=UIClass.SWIMMING_POOL,
        turn_on=lambda execute_command: execute_command(OverkizCommand.ON),
        turn_off=lambda execute_command: execute_command(OverkizCommand.OFF),
        is_on=lambda select_state: (
            select_state(OverkizState.CORE_ON_OFF) == OverkizCommandParam.ON
        ),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Overkiz switch from a config entry."""
    data: HomeAssistantOverkizData = hass.data[DOMAIN][entry.entry_id]
    entities: list[OverkizSwitch] = []

    key_supported_devices = {
        description.key: description for description in SWITCH_DESCRIPTIONS
    }

    for device in data.platforms[Platform.SWITCH]:
        if description := key_supported_devices.get(
            device.widget
        ) or key_supported_devices.get(device.ui_class):
            entities.append(
                OverkizSwitch(
                    device.device_url,
                    data.coordinator,
                    description,
                )
            )

    async_add_entities(entities)


class OverkizSwitch(OverkizDescriptiveEntity, SwitchEntity):
    """Representation an Overkiz Switch."""

    entity_description: OverkizSwitchDescription

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        return self.entity_description.is_on(self.executor.select_state)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.entity_description.turn_on(self.executor.async_execute_command)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.entity_description.turn_off(self.executor.async_execute_command)
