"""Switches for AVM Fritz!Box buttons."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Final

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common import AvmWrapper, FritzData, FritzDevice, FritzDeviceBase, _is_tracked
from .const import BUTTON_TYPE_WOL, DATA_FRITZ, DOMAIN, MeshRoles

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FritzButtonDescriptionMixin:
    """Mixin to describe a Button entity."""

    press_action: Callable


@dataclass(frozen=True)
class FritzButtonDescription(ButtonEntityDescription, FritzButtonDescriptionMixin):
    """Class to describe a Button entity."""


BUTTONS: Final = [
    FritzButtonDescription(
        key="firmware_update",
        translation_key="firmware_update",
        device_class=ButtonDeviceClass.UPDATE,
        entity_category=EntityCategory.CONFIG,
        press_action=lambda avm_wrapper: avm_wrapper.async_trigger_firmware_update(),
    ),
    FritzButtonDescription(
        key="reboot",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        press_action=lambda avm_wrapper: avm_wrapper.async_trigger_reboot(),
    ),
    FritzButtonDescription(
        key="reconnect",
        translation_key="reconnect",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        press_action=lambda avm_wrapper: avm_wrapper.async_trigger_reconnect(),
    ),
    FritzButtonDescription(
        key="cleanup",
        translation_key="cleanup",
        icon="mdi:broom",
        entity_category=EntityCategory.CONFIG,
        press_action=lambda avm_wrapper: avm_wrapper.async_trigger_cleanup(),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set buttons for device."""
    _LOGGER.debug("Setting up buttons")
    avm_wrapper: AvmWrapper = hass.data[DOMAIN][entry.entry_id]

    entities_list = [FritzButton(avm_wrapper, entry.title, button) for button in BUTTONS]

    if avm_wrapper.mesh_role == MeshRoles.SLAVE:
        async_add_entities(entities_list)
        return

    data_fritz: FritzData = hass.data[DATA_FRITZ]
    entities_list += await _async_wol_buttons_list(avm_wrapper, data_fritz)

    async_add_entities(entities_list)

    @callback
    async def async_update_avm_device() -> None:
        """Update the values of the AVM device."""
        async_add_entities(await _async_wol_buttons_list(avm_wrapper, data_fritz))

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, avm_wrapper.signal_device_new, async_update_avm_device
        )
    )


class FritzButton(ButtonEntity):
    """Defines a Fritz!Box base button."""

    entity_description: FritzButtonDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        avm_wrapper: AvmWrapper,
        device_friendly_name: str,
        description: FritzButtonDescription,
    ) -> None:
        """Initialize Fritz!Box button."""
        self.entity_description = description
        self.avm_wrapper = avm_wrapper

        self._attr_unique_id = f"{self.avm_wrapper.unique_id}-{description.key}"

        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, avm_wrapper.mac)},
            name=device_friendly_name,
        )

    async def async_press(self) -> None:
        """Triggers Fritz!Box service."""
        await self.entity_description.press_action(self.avm_wrapper)


async def _async_wol_buttons_list(
    avm_wrapper: AvmWrapper,
    data_fritz: FritzData,
) -> list[FritzBoxWOLButton]:
    """Add new WOL button entities from the AVM device."""
    _LOGGER.debug("Setting up %s buttons", BUTTON_TYPE_WOL)

    new_wols: list[FritzBoxWOLButton] = []

    if avm_wrapper.unique_id not in data_fritz.wol_buttons:
        data_fritz.wol_buttons[avm_wrapper.unique_id] = set()

    for mac, device in avm_wrapper.devices.items():
        if _is_tracked(mac, data_fritz.wol_buttons.values()):
            _LOGGER.debug("Skipping wol button creation for device %s", device.hostname)
            continue

        new_wols.append(FritzBoxWOLButton(avm_wrapper, device))
        data_fritz.wol_buttons[avm_wrapper.unique_id].add(mac)

    _LOGGER.debug("Creating %s wol buttons", len(new_wols))
    return new_wols


class FritzBoxWOLButton(FritzDeviceBase, ButtonEntity):
    """Defines a FRITZ!Box Tools Wake On LAN button."""

    _attr_icon = "mdi:lan-pending"

    def __init__(self, avm_wrapper: AvmWrapper, device: FritzDevice) -> None:
        """Initialize Fritz!Box WOL button."""
        super().__init__(avm_wrapper, device)
        self._name = f"{device.hostname} Wake on LAN"
        self._attr_unique_id = f"{self._mac}_wake_on_lan"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, self._mac)},
            default_manufacturer="AVM",
            default_model="FRITZ!Box Tracked device",
            default_name=device.hostname,
            via_device=(
                DOMAIN,
                avm_wrapper.unique_id,
            ),
        )

    @property
    def available(self) -> bool:
        """Return availability of the button."""
        return super().available

    async def async_press(self) -> None:
        """Press the button."""
        if self.mac_address:
            await self._avm_wrapper.async_wake_on_lan(self.mac_address)
