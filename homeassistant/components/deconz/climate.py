"""Support for deCONZ climate devices."""
from pydeconz.sensor import Thermostat

from homeassistant.components.climate import DOMAIN, ClimateEntity
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    FAN_ON,
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_FAN_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import ATTR_OFFSET, ATTR_VALVE, NEW_SENSOR
from .deconz_device import DeconzDevice
from .gateway import get_gateway_from_config_entry

FAN_MODES = {
    FAN_AUTO: "auto",
    FAN_HIGH: "high",
    FAN_LOW: "low",
    FAN_MEDIUM: "medium",
    FAN_OFF: "off",
    FAN_ON: "on",
}

HVAC_MODES = {
    HVAC_MODE_AUTO: "auto",
    HVAC_MODE_HEAT: "heat",
    HVAC_MODE_OFF: "off",
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the deCONZ climate devices.

    Thermostats are based on the same device class as sensors in deCONZ.
    """
    gateway = get_gateway_from_config_entry(hass, config_entry)
    gateway.entities[DOMAIN] = set()

    @callback
    def async_add_climate(sensors):
        """Add climate devices from deCONZ."""
        entities = []

        for sensor in sensors:

            if (
                sensor.type in Thermostat.ZHATYPE
                and sensor.uniqueid not in gateway.entities[DOMAIN]
                and (
                    gateway.option_allow_clip_sensor
                    or not sensor.type.startswith("CLIP")
                )
            ):
                entities.append(DeconzThermostat(sensor, gateway))

        if entities:
            async_add_entities(entities)

    gateway.listeners.append(
        async_dispatcher_connect(
            hass, gateway.async_signal_new_device(NEW_SENSOR), async_add_climate
        )
    )

    async_add_climate(gateway.api.sensors.values())


class DeconzThermostat(DeconzDevice, ClimateEntity):
    """Representation of a deCONZ thermostat."""

    TYPE = DOMAIN

    def __init__(self, device, gateway):
        """Set up thermostat device."""
        super().__init__(device, gateway)

        self._features = SUPPORT_TARGET_TEMPERATURE

        if device.fanmode is not None:
            self._features |= SUPPORT_FAN_MODE

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._features

    @property
    def fan_mode(self) -> str:
        """Return fan operation."""
        for hass_fan_mode, fan_mode in FAN_MODES.items():
            if self._device.fanmode == fan_mode:
                return hass_fan_mode

        if self._device.state_on:
            return FAN_ON

        return FAN_OFF

    @property
    def fan_modes(self) -> list:
        """Return the list of available fan operation modes."""
        return list(FAN_MODES)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if fan_mode not in FAN_MODES:
            raise ValueError(f"Unsupported mode {fan_mode}")

        data = {"fanmode": FAN_MODES[fan_mode]}

        await self._device.async_set_config(data)

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.

        Need to be one of HVAC_MODE_*.
        """
        for hass_hvac_mode, device_mode in HVAC_MODES.items():
            if self._device.mode == device_mode:
                return hass_hvac_mode

        if self._device.state_on:
            return HVAC_MODE_HEAT

        return HVAC_MODE_OFF

    @property
    def hvac_modes(self) -> list:
        """Return the list of available hvac operation modes."""
        return list(HVAC_MODES)

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._device.temperature

    @property
    def target_temperature(self):
        """Return the target temperature."""
        return self._device.heatsetpoint

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if ATTR_TEMPERATURE not in kwargs:
            raise ValueError(f"Expected attribute {ATTR_TEMPERATURE}")

        data = {"heatsetpoint": kwargs[ATTR_TEMPERATURE] * 100}

        await self._device.async_set_config(data)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode not in HVAC_MODES:
            raise ValueError(f"Unsupported mode {hvac_mode}")

        data = {"mode": HVAC_MODES[hvac_mode]}

        await self._device.async_set_config(data)

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def device_state_attributes(self):
        """Return the state attributes of the thermostat."""
        attr = {}

        if self._device.offset:
            attr[ATTR_OFFSET] = self._device.offset

        if self._device.valve is not None:
            attr[ATTR_VALVE] = self._device.valve

        return attr
