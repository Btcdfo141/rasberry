"""Button support for Bravia TV."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BraviaTVCoordinator
from .entity import BraviaTVEntity


@dataclass
class BraviaTVButtonDescriptionMixin:
    """Mixin to describe a Bravia TV Button entity."""

    press_action: Callable


@dataclass
class BraviaTVButtonDescription(
    ButtonEntityDescription, BraviaTVButtonDescriptionMixin
):
    """Bravia TV Button description."""


BUTTONS: tuple[BraviaTVButtonDescription, ...] = (
    BraviaTVButtonDescription(
        key="reboot",
        name="Reboot",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        press_action=lambda coordinator: coordinator.async_reboot_device(),
    ),
    BraviaTVButtonDescription(
        key="terminate_apps",
        name="Terminate apps",
        entity_category=EntityCategory.CONFIG,
        press_action=lambda coordinator: coordinator.async_terminate_apps(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Bravia TV Button entities."""

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    unique_id = config_entry.unique_id
    assert unique_id is not None

    async_add_entities(
        BraviaTVButton(coordinator, unique_id, config_entry.title, description)
        for description in BUTTONS
    )


class BraviaTVButton(BraviaTVEntity, ButtonEntity):
    """Representation of a Bravia TV Button."""

    entity_description: BraviaTVButtonDescription

    def __init__(
        self,
        coordinator: BraviaTVCoordinator,
        unique_id: str,
        model: str,
        description: BraviaTVButtonDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, unique_id, model)
        self._attr_unique_id = f"{unique_id}_{description.key}"
        self.entity_description = description

    async def async_press(self) -> None:
        """Trigger the button action."""
        await self.entity_description.press_action(self.coordinator)
