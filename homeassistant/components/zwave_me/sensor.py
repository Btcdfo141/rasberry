"""Representation of a sensorMultilevel."""
from __future__ import annotations

from zwave_me_ws import ZWaveMeData

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ELECTRIC_POTENTIAL_VOLT,
    ENERGY_KILO_WATT_HOUR,
    LIGHT_LUX,
    POWER_WATT,
    SIGNAL_STRENGTH_DECIBELS,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ZWaveMeController, ZWaveMeEntity
from .const import DOMAIN

SENSORS_MAP: dict[str, SensorEntityDescription] = {
    "meterElectric_watt": SensorEntityDescription(
        key="meterElectric_watt",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=POWER_WATT,
    ),
    "meterElectric_kilowatt_hour": SensorEntityDescription(
        key="meterElectric_kilowatt_hour",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    ),
    "meterElectric_voltage": SensorEntityDescription(
        key="meterElectric_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
    ),
    "light": SensorEntityDescription(
        key="light",
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
    ),
    "noise": SensorEntityDescription(
        key="noise",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
    ),
    "currentTemperature": SensorEntityDescription(
        key="currentTemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
    "temperature": SensorEntityDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
    "generic": SensorEntityDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
}
DEVICE_NAME = "sensorMultilevel"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""

    @callback
    def add_new_device(new_device: ZWaveMeData) -> None:
        controller: ZWaveMeController = hass.data[DOMAIN][config_entry.entry_id]
        description = get_description(new_device)
        sensor = ZWaveMeSensor(controller, new_device, description)

        async_add_entities(
            [
                sensor,
            ]
        )

    @callback
    def get_description(new_device: ZWaveMeData) -> SensorEntityDescription:
        if new_device.probeType in SENSORS_MAP:
            return SENSORS_MAP.get(new_device.probeType)
        return SENSORS_MAP["generic"]

    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"ZWAVE_ME_NEW_{DEVICE_NAME.upper()}", add_new_device
        )
    )


class ZWaveMeSensor(ZWaveMeEntity, SensorEntity):
    """Representation of a ZWaveMe sensor."""

    def __init__(
        self,
        controller: ZWaveMeController,
        device: ZWaveMeData,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the device."""
        super().__init__(controller=controller, device=device)
        self.entity_description = description

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self.device.level
