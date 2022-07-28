"""Plugwise Climate component for Home Assistant."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_MAX_TEMP, DEFAULT_MIN_TEMP, DOMAIN, MASTER_THERMOSTATS
from .coordinator import PlugwiseDataUpdateCoordinator
from .entity import PlugwiseEntity
from .util import plugwise_command


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Smile Thermostats from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        PlugwiseClimateEntity(coordinator, device_id)
        for device_id, device in coordinator.data.devices.items()
        if device["dev_class"] in MASTER_THERMOSTATS
    )


class PlugwiseClimateEntity(PlugwiseEntity, ClimateEntity):
    """Representation of an Plugwise thermostat."""

    _attr_temperature_unit = TEMP_CELSIUS
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PlugwiseDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Set up the Plugwise API."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-climate"

        if presets := self.device.get("preset_modes"):
            self._attr_preset_modes = presets

        self._attr_min_temp = self.device["thermostat"].get(
            "lower_bound", DEFAULT_MIN_TEMP
        )
        self._attr_max_temp = self.device["thermostat"].get(
            "upper_bound", DEFAULT_MAX_TEMP
        )
        if resolution := self.device["thermostat"].get("resolution", 0.1):
            # Ensure we don't drop below 0.1
            self._attr_target_temperature_step = max(resolution, 0.1)

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return self.device["sensors"]["temperature"]

    @property
    def hvac_action(self) -> HVACAction:
        """Return the current running hvac operation if supported."""
        # When control_state is present, prefer this data
        control_state: str = self.device.get("control_state", "not_found")
        if control_state == "cooling":
            return HVACAction.COOLING
        # Support preheating state as heating, until preheating is added as a separate state
        if control_state in ["heating", "preheating"]:
            return HVACAction.HEATING
        if control_state == "off":
            return HVACAction.IDLE

        heater_central_data = self.devices[self.gateway["heater_id"]]
        if heater_central_data["binary_sensors"]["heating_state"]:
            return HVACAction.HEATING
        if heater_central_data["binary_sensors"].get("cooling_state", False):
            return HVACAction.COOLING

        return HVACAction.IDLE

    @property
    def hvac_mode(self) -> HVACMode:
        """Return HVAC operation ie. auto, heat, cool, or off mode."""
        if (mode := self.device["mode"]) is None or mode not in self.hvac_modes:
            return HVACMode.HEAT  # pragma: no cover

        return HVACMode(mode)

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the current hvac modes."""
        hvac_modes = [HVACMode.HEAT]
        if self.gateway["cooling_present"]:
            if self.gateway["smile_name"] == "Anna":
                hvac_modes.append(HVACMode.HEAT_COOL)
                hvac_modes.remove(HVACMode.HEAT)
            if (
                self.gateway["smile_name"] == "Adam"
                and self.devices[self.gateway["gateway_id"]]["regulation_mode"]
                == "cooling"
            ):
                hvac_modes.append(HVACMode.COOL)
                hvac_modes.remove(HVACMode.HEAT)
        if self.device["available_schedules"] != ["None"]:
            hvac_modes.append(HVACMode.AUTO)

        return hvac_modes

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode."""
        return self.device["active_preset"]

    @property
    def supported_features(self) -> int:
        """Return the supported features."""
        features: int = ClimateEntityFeature.TARGET_TEMPERATURE
        if self.coordinator.api.elga_cooling_enabled:
            features = ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        if self.device.get("preset_modes"):
            features |= ClimateEntityFeature.PRESET_MODE

        return features

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach.

        Connected to the HVACModes combinations of AUTO/HEAT and AUTO/COOL.
        """

        return self.device["thermostat"].get("setpoint")

    @property
    def target_temperature_high(self) -> float | None:
        """Return the temperature we try to reach in case of cooling.

        Connected to the HVACMode combination of AUTO/HEAT_COOL.
        """
        return self.device["thermostat"].get("setpoint_high")

    @property
    def target_temperature_low(self) -> float | None:
        """Return the heating temperature we try to reach in case of heating.

        Connected to the HVACMode combination AUTO/HEAT_COOL.
        """
        return self.device["thermostat"].get("setpoint_low")

    @plugwise_command
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        data: dict[str, Any] = {}
        if ATTR_TEMPERATURE in kwargs:
            data["setpoint"] = kwargs.get(ATTR_TEMPERATURE)
        if ATTR_TARGET_TEMP_HIGH in kwargs:
            data["setpoint_high"] = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        if ATTR_TARGET_TEMP_LOW in kwargs:
            data["setpoint_low"] = kwargs.get(ATTR_TARGET_TEMP_LOW)

        for _, temperature in data.items():
            if temperature is None or not (
                self._attr_min_temp <= temperature <= self._attr_max_temp
            ):
                raise ValueError("Invalid temperature change requested")

        await self.coordinator.api.set_temperature(self.device["location"], data)

    @plugwise_command
    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set the hvac mode."""
        if hvac_mode not in self.hvac_modes:
            raise HomeAssistantError("Unsupported hvac_mode")

        await self.coordinator.api.set_schedule_state(
            self.device["location"],
            self.device["last_used"],
            "on" if hvac_mode == HVACMode.AUTO else "off",
        )

    @plugwise_command
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode."""
        await self.coordinator.api.set_preset(self.device["location"], preset_mode)
