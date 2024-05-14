"""Support for TPLink Fan devices."""

import logging
import math
from typing import Any

from kasa import Device
from kasa.smart import SmartDevice

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)
from homeassistant.util.scaling import int_states_in_range

from .const import DOMAIN
from .coordinator import TPLinkDataUpdateCoordinator
from .entity import CoordinatedTPLinkEntity, async_refresh_after
from .models import TPLinkData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up fans."""
    data: TPLinkData = hass.data[DOMAIN][config_entry.entry_id]
    parent_coordinator = data.parent_coordinator
    device = parent_coordinator.device
    entities: list = []
    if not isinstance(device, SmartDevice):
        return
    if device.is_fan:
        entities.append(TPLinkFan(device, parent_coordinator))
    for child in device.children:
        if child.is_fan:
            entities.append(TPLinkFan(child, parent_coordinator, parent=device))
            # Add fan control to the parent if the parent is not a fan.
            if not device.is_fan:
                entities.append(
                    TPLinkFan(
                        child, parent_coordinator, parent=device, add_to_parent=True
                    )
                )

    async_add_entities(entities)


SPEED_RANGE = (1, 4)  # off is not included


class TPLinkFan(CoordinatedTPLinkEntity, FanEntity):
    """Representation of a fan for a TPLink Fan device."""

    device: SmartDevice
    _attr_speed_count = int_states_in_range(SPEED_RANGE)
    _attr_supported_features = FanEntityFeature.SET_SPEED
    _attr_name = None

    def __init__(
        self,
        device: Device,
        coordinator: TPLinkDataUpdateCoordinator,
        parent: Device | None = None,
        *,
        add_to_parent: bool = False,
    ) -> None:
        """Initialize the fan."""
        super().__init__(device, coordinator, parent, add_to_parent=add_to_parent)
        self._async_update_attrs()

    @async_refresh_after
    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        value_in_range = (
            math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
            if percentage is not None
            else None
        )
        if value_in_range:
            await self.device.set_fan_speed_level(value_in_range)
        else:
            await self.device.turn_on()  # type: ignore[no-untyped-call]

    @async_refresh_after
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        await self.device.turn_off()  # type: ignore[no-untyped-call]

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        value_in_range = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
        await self.device.set_fan_speed_level(value_in_range)

    @callback
    def _async_update_attrs(self) -> None:
        """Update the entity's attributes."""
        self._attr_is_on = self.device.is_on
        self._attr_percentage = (
            ranged_value_to_percentage(SPEED_RANGE, self.device.fan_speed_level)
            if self._attr_is_on
            else None
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._async_update_attrs()
        super()._handle_coordinator_update()
