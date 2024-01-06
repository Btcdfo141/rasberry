"""Lutron fan platform."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, LutronData
from .entity import LutronDevice

_LOGGER = logging.getLogger(__name__)

PRESET_MODE_AUTO = "auto"
PRESET_MODE_SMART = "smart"
PRESET_MODE_SLEEP = "sleep"
PRESET_MODE_ON = "on"

FULL_SUPPORT = (
    FanEntityFeature.SET_SPEED | FanEntityFeature.OSCILLATE | FanEntityFeature.DIRECTION
)
LIMITED_SUPPORT = FanEntityFeature.SET_SPEED


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Lutron fan platform.

    Adds fan controls from the Main Repeater associated with the config_entry as
    fan entities.
    """
    entry_data: LutronData = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            LutronFan(area_name, device, entry_data.client)
            for area_name, device in entry_data.fans
        ],
        True,
    )


class LutronFan(LutronDevice, FanEntity):
    """Representation of a Lutron fan."""

    _attr_preset_mode = None
    _attr_preset_modes = None
    _attr_should_poll = False
    _attr_speed_count = 3
    _attr_supported_features = FanEntityFeature.SET_SPEED

    def __init__(
        self,
        area_name,
        lutron_device,
        controller,
    ) -> None:
        """Initialize the fan."""

        super().__init__(area_name, lutron_device, controller)
        self._attr_extra_state_attributes = {
            "lutron_integration_id": self._lutron_device.id
        }
        self._prev_percentage: int | None = None
        self._percentage: int | None = None
        self._oscillating: bool | None = None
        self._direction: str | None = None

    @property
    def percentage(self) -> int | None:
        """Return the current speed."""
        new_percentage = self._lutron_device.last_level()
        if new_percentage != 0:
            self._prev_percentage = new_percentage
        return new_percentage

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        if percentage is None:
            percentage = 0
        if percentage > 0:
            self._prev_percentage = percentage
        self._percentage = percentage
        self._lutron_device.level = percentage
        self._attr_preset_mode = None
        self.async_write_ha_state()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the fan on."""
        new_percentage: int | None = None

        if preset_mode:
            await self.async_set_preset_mode(preset_mode)
            return
        if percentage is not None:
            new_percentage = percentage
        elif self._prev_percentage == 0:
            # Default to medium speed
            new_percentage = 67
        elif self._prev_percentage is None:
            # Default to medium speed
            new_percentage = 67
        else:
            new_percentage = self._prev_percentage
        await self.async_set_percentage(new_percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        await self.async_set_percentage(0)

    def update(self) -> None:
        """Call when forcing a refresh of the device."""

        # Reading the property (rather than last_level()) fetches value
        level = self._lutron_device.level
        _LOGGER.debug("Lutron ID: %d updated to %f", self._lutron_device.id, level)
        if self._prev_percentage is None:
            self._prev_percentage = self._lutron_device.level
