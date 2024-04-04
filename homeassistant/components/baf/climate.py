"""Support for Big Ass Fans auto comfort."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import BAFEntity
from .models import BAFData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BAF fan auto comfort."""
    data: BAFData = hass.data[DOMAIN][entry.entry_id]
    if data.device.has_fan and data.device.has_auto_comfort:
        async_add_entities([BAFAutoComfort(data.device)])


class BAFAutoComfort(BAFEntity, ClimateEntity):
    """BAF climate auto comfort."""

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.FAN_ONLY]
    _attr_translation_key = "auto_comfort"
    _enable_turn_on_off_backwards_compatibility = False

    @callback
    def _async_update_attrs(self) -> None:
        """Update attrs from device."""
        device = self._device
        auto_on = device.auto_comfort_enable
        self._attr_hvac_mode = HVACMode.FAN_ONLY if auto_on else HVACMode.OFF
        self._attr_hvac_action = HVACAction.FAN if device.speed else HVACAction.OFF
        self._attr_target_temperature = device.comfort_ideal_temperature
        self._attr_current_temperature = device.temperature

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        self._device.auto_comfort_enable = hvac_mode == HVACMode.FAN_ONLY

    async def async_set_target_temperature(
        self,
        temperature: float,
        hvac_mode: HVACMode | None = None,
    ) -> None:
        """Set the target temperature."""
        if not self._device.auto_comfort_enable:
            self._device.auto_comfort_enable = True
        self._device.comfort_ideal_temperature = temperature
