"""Support for Netgear Button."""
from collections.abc import Callable, Coroutine
from dataclasses import dataclass

from typing import Any

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, KEY_COORDINATOR, KEY_ROUTER
from .router import NetgearRouter, NetgearRouterEntity


@dataclass
class NetgearButtonEntityDescriptionRequired:
    """Required attributes of NetgearButtonEntityDescription."""

    action: Callable[[NetgearRouter], Callable[[], Coroutine[Any, Any, None]]]


@dataclass
class NetgearButtonEntityDescription(
    ButtonEntityDescription, NetgearButtonEntityDescriptionRequired
):
    """Class describing Netgear button entities."""


BUTTONS = [
    NetgearButtonEntityDescription(
        key="reboot",
        name="Reboot",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        action=lambda router: router.async_reboot,
    )
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up button for Netgear component."""
    router = hass.data[DOMAIN][entry.entry_id][KEY_ROUTER]
    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    async_add_entities(
        NetgearRouterButtonEntity(coordinator, router, entity_description)
        for entity_description in BUTTONS
    )


class NetgearRouterButtonEntity(NetgearRouterEntity, ButtonEntity):
    """Netgear Router button entity."""

    entity_description: NetgearButtonEntityDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        router: NetgearRouter,
        entity_description: NetgearButtonEntityDescription,
    ) -> None:
        """Initialize a Netgear device."""
        super().__init__(coordinator, router)
        self.entity_description = entity_description
        self._name = f"{router.device_name} {entity_description.name}"
        self._unique_id = f"{router.serial_number}-{entity_description.key}"

    async def async_press(self) -> None:
        """Triggers the button press service."""
        async_action = self.entity_description.action(self._router)
        await async_action()

    @callback
    def async_update_device(self) -> None:
        """Update the Netgear device."""
