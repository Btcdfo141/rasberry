"""Switch platform for MicroBot."""
from __future__ import annotations
from typing import Any

from homeassistant.components.switch import SwitchEntity

from .const import DEFAULT_NAME, DOMAIN, ICON
from .entity import MicroBotEntity


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MicroBot based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MicroBotBinarySwitch(coordinator, entry)])


class MicroBotBinarySwitch(MicroBotEntity, SwitchEntity):
    """MicroBot switch class."""
    _attr_icon = ICON
    _attr_name = f"{DEFAULT_NAME}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.coordinator.api.push_on()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.coordinator.api.push_off()
        self.async_write_ha_state()

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self.coordinator.api.is_on
