"""Support for Steamist switches."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .entity import SteamistEntity

ACTIVE_SWITCH = SwitchEntityDescription(
    key="active", icon="mdi:pot-steam", name="Steam Active"
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([SteamistSwitchEntity(coordinator, config_entry, ACTIVE_SWITCH)])


class SteamistSwitchEntity(SteamistEntity, SwitchEntity):
    """Representation of an Steamist binary sensor."""

    @property
    def is_on(self) -> bool:
        """Return if the steam is active."""
        return self._status.active

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the steam on."""
        await self.coordinator.client.async_turn_on_steam()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the steam off."""
        await self.coordinator.client.async_turn_off_steam()
        await self.coordinator.async_request_refresh()
