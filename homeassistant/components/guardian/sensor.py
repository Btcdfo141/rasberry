"""Sensors for the Elexa Guardian integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, TEMP_FAHRENHEIT, TIME_MINUTES
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import (
    PairedSensorEntity,
    ValveControllerEntity,
    ValveControllerEntityDescription,
)
from .const import (
    API_SYSTEM_DIAGNOSTICS,
    API_SYSTEM_ONBOARD_SENSOR_STATUS,
    CONF_UID,
    DATA_COORDINATOR,
    DATA_COORDINATOR_PAIRED_SENSOR,
    DOMAIN,
    SIGNAL_PAIRED_SENSOR_COORDINATOR_ADDED,
)

SENSOR_KIND_BATTERY = "battery"
SENSOR_KIND_TEMPERATURE = "temperature"
SENSOR_KIND_UPTIME = "uptime"


@dataclass
class ValveControllerSensorDescription(
    SensorEntityDescription, ValveControllerEntityDescription
):
    """Describe a Guardian valve controller sensor."""


PAIRED_SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key=SENSOR_KIND_BATTERY,
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SensorEntityDescription(
        key=SENSOR_KIND_TEMPERATURE,
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=TEMP_FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)
VALVE_CONTROLLER_DESCRIPTIONS = (
    ValveControllerSensorDescription(
        key=SENSOR_KIND_TEMPERATURE,
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=TEMP_FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
        api_category=API_SYSTEM_ONBOARD_SENSOR_STATUS,
    ),
    ValveControllerSensorDescription(
        key=SENSOR_KIND_UPTIME,
        name="Uptime",
        icon="mdi:timer",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=TIME_MINUTES,
        api_category=API_SYSTEM_DIAGNOSTICS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Guardian switches based on a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    paired_sensor_coordinators = entry_data[DATA_COORDINATOR_PAIRED_SENSOR]
    valve_controller_coordinators = entry_data[DATA_COORDINATOR]

    @callback
    def add_new_paired_sensor(uid: str) -> None:
        """Add a new paired sensor."""
        async_add_entities(
            PairedSensorSensor(entry, paired_sensor_coordinators[uid], description)
            for description in PAIRED_SENSOR_DESCRIPTIONS
        )

    # Handle adding paired sensors after HASS startup:
    entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            SIGNAL_PAIRED_SENSOR_COORDINATOR_ADDED.format(entry.data[CONF_UID]),
            add_new_paired_sensor,
        )
    )

    # Add all valve controller-specific binary sensors:
    sensors: list[PairedSensorSensor | ValveControllerSensor] = [
        ValveControllerSensor(entry, valve_controller_coordinators, description)
        for description in VALVE_CONTROLLER_DESCRIPTIONS
    ]

    # Add all paired sensor-specific binary sensors:
    sensors.extend(
        [
            PairedSensorSensor(entry, coordinator, description)
            for coordinator in paired_sensor_coordinators.values()
            for description in PAIRED_SENSOR_DESCRIPTIONS
        ]
    )

    async_add_entities(sensors)


class PairedSensorSensor(PairedSensorEntity, SensorEntity):
    """Define a binary sensor related to a Guardian valve controller."""

    entity_description: SensorEntityDescription

    @callback
    def _async_update_from_latest_data(self) -> None:
        """Update the entity."""
        if self.entity_description.key == SENSOR_KIND_BATTERY:
            self._attr_native_value = self.coordinator.data["battery"]
        elif self.entity_description.key == SENSOR_KIND_TEMPERATURE:
            self._attr_native_value = self.coordinator.data["temperature"]


class ValveControllerSensor(ValveControllerEntity, SensorEntity):
    """Define a generic Guardian sensor."""

    entity_description: ValveControllerSensorDescription

    @callback
    def _async_update_from_latest_data(self) -> None:
        """Update the entity."""
        if self.entity_description.key == SENSOR_KIND_TEMPERATURE:
            self._attr_native_value = self.coordinator.data["temperature"]
        elif self.entity_description.key == SENSOR_KIND_UPTIME:
            self._attr_native_value = self.coordinator.data["uptime"]
