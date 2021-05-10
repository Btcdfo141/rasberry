"""Support for Honeywell (US) Total Connect Comfort climate systems."""
from __future__ import annotations

import datetime
from homeassistant.helpers.typing import ConfigType
from homeassistant.core import HomeAssistant
import logging
from typing import Any

import somecomfort

from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_FAN,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    FAN_AUTO,
    FAN_DIFFUSE,
    FAN_ON,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_NONE,
    SUPPORT_AUX_HEAT,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_HUMIDITY,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PERCENTAGE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ATTR_FAN_ACTION = "fan_action"

ATTR_PERMANENT_HOLD = "permanent_hold"

HVAC_MODE_TO_HW_MODE = {
    "SwitchOffAllowed": {HVAC_MODE_OFF: "off"},
    "SwitchAutoAllowed": {HVAC_MODE_HEAT_COOL: "auto"},
    "SwitchCoolAllowed": {HVAC_MODE_COOL: "cool"},
    "SwitchHeatAllowed": {HVAC_MODE_HEAT: "heat"},
}
HW_MODE_TO_HVAC_MODE = {
    "off": HVAC_MODE_OFF,
    "emheat": HVAC_MODE_HEAT,
    "heat": HVAC_MODE_HEAT,
    "cool": HVAC_MODE_COOL,
    "auto": HVAC_MODE_HEAT_COOL,
}
HW_MODE_TO_HA_HVAC_ACTION = {
    "off": CURRENT_HVAC_IDLE,
    "fan": CURRENT_HVAC_FAN,
    "heat": CURRENT_HVAC_HEAT,
    "cool": CURRENT_HVAC_COOL,
}
FAN_MODE_TO_HW = {
    "fanModeOnAllowed": {FAN_ON: "on"},
    "fanModeAutoAllowed": {FAN_AUTO: "auto"},
    "fanModeCirculateAllowed": {FAN_DIFFUSE: "circulate"},
}
HW_FAN_MODE_TO_HA = {
    "on": FAN_ON,
    "auto": FAN_AUTO,
    "circulate": FAN_DIFFUSE,
    "follow schedule": FAN_AUTO,
}
SENSOR_TYPES = {
    "temperature": ["Temperature", TEMP_FAHRENHEIT],
    "humidity": ["Humidity", PERCENTAGE],
}

def setup_platform(
    hass: HomeAssistant, config: ConfigType, add_entities, discovery_info=None
) -> None:
    """Set up the Honeywell thermostat."""
    # TODO: Find out how to default these optional config items
    # cool_away_temp = None #config[DOMAIN][CONF_COOL_AWAY_TEMPERATURE]
    # heat_away_temp = None #config[DOMAIN][CONF_HEAT_AWAY_TEMPERATURE]

    add_entities(
        [
            HoneywellUSThermostat(
                hass.data[DOMAIN]["device"],
                None,
                None
            )
        ]
    )

class HoneywellUSThermostat(ClimateEntity):
    """Representation of a Honeywell US Thermostat."""

    def __init__(
        self, device, cool_away_temp, heat_away_temp
    ):
        """Initialize the thermostat."""
        self._device = device
        self._cool_away_temp = cool_away_temp
        self._heat_away_temp = heat_away_temp
        self._away = False

        _LOGGER.debug("latestData = %s ", device._data)

        # not all honeywell HVACs support all modes
        mappings = [v for k, v in HVAC_MODE_TO_HW_MODE.items() if device.raw_ui_data[k]]
        self._hvac_mode_map = {k: v for d in mappings for k, v in d.items()}

        self._supported_features = (
            SUPPORT_PRESET_MODE
            | SUPPORT_TARGET_TEMPERATURE
            | SUPPORT_TARGET_TEMPERATURE_RANGE
        )

        if device._data["canControlHumidification"]:
            self._supported_features |= SUPPORT_TARGET_HUMIDITY

        if device.raw_ui_data["SwitchEmergencyHeatAllowed"]:
            self._supported_features |= SUPPORT_AUX_HEAT

        if not device._data["hasFan"]:
            return

        # not all honeywell fans support all modes
        mappings = [v for k, v in FAN_MODE_TO_HW.items() if device.raw_fan_data[k]]
        self._fan_mode_map = {k: v for d in mappings for k, v in d.items()}

        self._supported_features |= SUPPORT_FAN_MODE

    @property
    def name(self) -> str | None:
        """Return the name of the honeywell, if any."""
        return self._device.name

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device specific state attributes."""
        data = {}
        data[ATTR_FAN_ACTION] = "running" if self._device.fan_running else "idle"
        data[ATTR_PERMANENT_HOLD] = self._is_permanent_hold()
        if self._device.raw_dr_data:
            data["dr_phase"] = self._device.raw_dr_data.get("Phase")
        return data

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return self._supported_features

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        if self.hvac_mode in [HVAC_MODE_COOL, HVAC_MODE_HEAT_COOL]:
            return self._device.raw_ui_data["CoolLowerSetptLimit"]
        if self.hvac_mode == HVAC_MODE_HEAT:
            return self._device.raw_ui_data["HeatLowerSetptLimit"]
        return None

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        if self.hvac_mode == HVAC_MODE_COOL:
            return self._device.raw_ui_data["CoolUpperSetptLimit"]
        if self.hvac_mode in [HVAC_MODE_HEAT, HVAC_MODE_HEAT_COOL]:
            return self._device.raw_ui_data["HeatUpperSetptLimit"]
        return None

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return TEMP_CELSIUS if self._device.temperature_unit == "C" else TEMP_FAHRENHEIT

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self._device.current_humidity

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        return HW_MODE_TO_HVAC_MODE[self._device.system_mode]

    @property
    def hvac_modes(self) -> list[str]:
        """Return the list of available hvac operation modes."""
        return list(self._hvac_mode_map)

    @property
    def hvac_action(self) -> str | None:
        """Return the current running hvac operation if supported."""
        if self.hvac_mode == HVAC_MODE_OFF:
            return None
        return HW_MODE_TO_HA_HVAC_ACTION[self._device.equipment_output_status]

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._device.current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_COOL:
            return self._device.setpoint_cool
        if self.hvac_mode == HVAC_MODE_HEAT:
            return self._device.setpoint_heat
        return None

    @property
    def target_temperature_high(self) -> float | None:
        """Return the highbound target temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_HEAT_COOL:
            return self._device.setpoint_cool
        return None

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_HEAT_COOL:
            return self._device.setpoint_heat
        return None

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., home, away, temp."""
        return PRESET_AWAY if self._away else None

    @property
    def preset_modes(self) -> list[str] | None:
        """Return a list of available preset modes."""
        return [PRESET_NONE, PRESET_AWAY]

    @property
    def is_aux_heat(self) -> str | None:
        """Return true if aux heater."""
        return self._device.system_mode == "emheat"

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        return HW_FAN_MODE_TO_HA[self._device.fan_mode]

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes."""
        return list(self._fan_mode_map)

    def _is_permanent_hold(self) -> bool:
        heat_status = self._device.raw_ui_data.get("StatusHeat", 0)
        cool_status = self._device.raw_ui_data.get("StatusCool", 0)
        return heat_status == 2 or cool_status == 2

    def _set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        try:
            # Get current mode
            mode = self._device.system_mode
            # Set hold if this is not the case
            if getattr(self._device, f"hold_{mode}") is False:
                # Get next period key
                next_period_key = f"{mode.capitalize()}NextPeriod"
                # Get next period raw value
                next_period = self._device.raw_ui_data.get(next_period_key)
                # Get next period time
                hour, minute = divmod(next_period * 15, 60)
                # Set hold time
                setattr(self._device, f"hold_{mode}", datetime.time(hour, minute))
            # Set temperature
            setattr(self._device, f"setpoint_{mode}", temperature)
        except somecomfort.SomeComfortError:
            _LOGGER.error("Temperature %.1f out of range", temperature)

    def set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if {HVAC_MODE_COOL, HVAC_MODE_HEAT} & set(self._hvac_mode_map):
            self._set_temperature(**kwargs)

        try:
            if HVAC_MODE_HEAT_COOL in self._hvac_mode_map:
                temperature = kwargs.get(ATTR_TARGET_TEMP_HIGH)
                if temperature:
                    self._device.setpoint_cool = temperature
                temperature = kwargs.get(ATTR_TARGET_TEMP_LOW)
                if temperature:
                    self._device.setpoint_heat = temperature
        except somecomfort.SomeComfortError as err:
            _LOGGER.error("Invalid temperature %s: %s", temperature, err)

    def set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        self._device.fan_mode = self._fan_mode_map[fan_mode]

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        self._device.system_mode = self._hvac_mode_map[hvac_mode]

    def _turn_away_mode_on(self) -> None:
        """Turn away on.

        Somecomfort does have a proprietary away mode, but it doesn't really
        work the way it should. For example: If you set a temperature manually
        it doesn't get overwritten when away mode is switched on.
        """
        self._away = True
        try:
            # Get current mode
            mode = self._device.system_mode
        except somecomfort.SomeComfortError:
            _LOGGER.error("Can not get system mode")
            return
        try:

            # Set permanent hold
            setattr(self._device, f"hold_{mode}", True)
            # Set temperature
            setattr(
                self._device, f"setpoint_{mode}", getattr(self, f"_{mode}_away_temp")
            )
        except somecomfort.SomeComfortError:
            _LOGGER.error(
                "Temperature %.1f out of range", getattr(self, f"_{mode}_away_temp")
            )

    def _turn_away_mode_off(self) -> None:
        """Turn away off."""
        self._away = False
        try:
            # Disabling all hold modes
            self._device.hold_cool = False
            self._device.hold_heat = False
        except somecomfort.SomeComfortError:
            _LOGGER.error("Can not stop hold mode")

    def set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == PRESET_AWAY:
            self._turn_away_mode_on()
        else:
            self._turn_away_mode_off()

    def turn_aux_heat_on(self) -> None:
        """Turn auxiliary heater on."""
        self._device.system_mode = "emheat"

    def turn_aux_heat_off(self) -> None:
        """Turn auxiliary heater off."""
        if HVAC_MODE_HEAT in self.hvac_modes:
            self.set_hvac_mode(HVAC_MODE_HEAT)
        else:
            self.set_hvac_mode(HVAC_MODE_OFF)