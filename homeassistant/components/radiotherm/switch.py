"""Support for radiotherm switches."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RadioThermUpdateCoordinator
from .entity import RadioThermostatEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches for a radiotherm device."""
    coordinator: RadioThermUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RadioThermHoldSwitch(coordinator)])


class RadioThermHoldSwitch(RadioThermostatEntity, SwitchEntity):
    """Provides radiotherm hold switch support."""

    def __init__(self, coordinator: RadioThermUpdateCoordinator) -> None:
        """Initialize the hold mode switch."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.init_data.name} Hold"
        self._attr_unique_id = f"{coordinator.init_data.mac}_hold"

    @property
    def icon(self) -> str:
        """Return the icon for the switch."""
        return "mdi:timer-off" if self.is_on else "mdi:timer"

    @callback
    def _process_data(self) -> None:
        """Update and validate the data from the thermostat."""
        data = self.data.tstat
        self._attr_is_on = bool(data["hold"])

    def _set_hold(self, hold: bool) -> None:
        """Set hold mode."""
        self.device.hold = bool(hold)

    async def _async_set_hold(self, hold: bool) -> None:
        """Set hold mode."""
        await self.hass.async_add_executor_job(self._set_hold, hold)
        self._attr_is_on = hold
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable permanent hold."""
        await self._async_set_hold(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable permanent hold."""
        await self._async_set_hold(False)
