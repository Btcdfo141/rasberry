"""Buttons for Hunter Douglas Powerview advanced features."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any, Final

from aiopvapi.resources.shade import BaseShade, factory as PvShade

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    COORDINATOR,
    DEVICE_INFO,
    DOMAIN,
    PV_API,
    PV_ROOM_DATA,
    PV_SHADE_DATA,
    ROOM_ID_IN_SHADE,
    ROOM_NAME_UNICODE,
)
from .coordinator import PowerviewShadeUpdateCoordinator
from .entity import ShadeEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class PowerviewButtonDescriptionMixin:
    """Mixin to describe a Button entity."""

    press_action: Callable


@dataclass
class PowerviewButtonDescription(
    ButtonEntityDescription, PowerviewButtonDescriptionMixin
):
    """Class to describe a Button entity."""


BUTTONS: Final = [
    PowerviewButtonDescription(
        key="calibrate",
        name="Calibrate",
        icon="mdi:swap-vertical-circle-outline",
        device_class=ButtonDeviceClass.UPDATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        press_action=lambda shade, button: shade.calibrate(),
    ),
    PowerviewButtonDescription(
        key="identify",
        name="Identify",
        icon="mdi:crosshairs-question",
        device_class=ButtonDeviceClass.UPDATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        press_action=lambda shade, button: shade.jog(),
    ),
    PowerviewButtonDescription(
        key="update",
        name="Force Update",
        icon="mdi:autorenew",
        device_class=ButtonDeviceClass.UPDATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        press_action=lambda shade, button: button.async_force_refresh(),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set buttons for device."""

    pv_data = hass.data[DOMAIN][entry.entry_id]
    room_data: dict[str | int, Any] = pv_data[PV_ROOM_DATA]
    shade_data = pv_data[PV_SHADE_DATA]
    pv_request = pv_data[PV_API]
    coordinator: PowerviewShadeUpdateCoordinator = pv_data[COORDINATOR]
    device_info: dict[str, Any] = pv_data[DEVICE_INFO]

    entities: list[ButtonEntity] = []
    for raw_shade in shade_data.values():
        shade: BaseShade = PvShade(raw_shade, pv_request)
        name_before_refresh = shade.name
        room_id = shade.raw_data.get(ROOM_ID_IN_SHADE)
        room_name = room_data.get(room_id, {}).get(ROOM_NAME_UNICODE, "")

        for description in BUTTONS:
            entities.append(
                PowerviewButton(
                    coordinator,
                    device_info,
                    room_name,
                    shade,
                    name_before_refresh,
                    description,
                )
            )

    async_add_entities(entities)


class PowerviewButton(ShadeEntity, ButtonEntity):
    """Representation of an advanced feature button."""

    def __init__(
        self,
        coordinator: PowerviewShadeUpdateCoordinator,
        device_info,
        room_name,
        shade,
        name,
        description: PowerviewButtonDescription,
    ):
        """Initialize the button entity."""
        super().__init__(coordinator, device_info, room_name, shade, name)
        self.entity_description: PowerviewButtonDescription = description
        self._attr_name = f"{self._shade_name} {description.name}"
        self._attr_unique_id = f"{self._attr_unique_id}_{description.key}"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.entity_description.press_action(self._shade, self)

    async def async_force_refresh(self) -> None:
        """Refresh shade position."""
        _LOGGER.debug("Manual update of shade data run for %s", self._shade_name)
        await self._shade.refresh()
        self.data.update_shade_positions(self._shade.raw_data)
        self.async_write_ha_state()
