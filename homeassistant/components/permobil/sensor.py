"""Platform for sensor integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from mypermobil import (
    BATTERY_AMPERE_HOURS_LEFT,
    BATTERY_CHARGE_TIME_LEFT,
    BATTERY_DISTANCE_LEFT,
    BATTERY_INDOOR_DRIVE_TIME,
    BATTERY_MAX_AMPERE_HOURS,
    BATTERY_MAX_DISTANCE_LEFT,
    BATTERY_STATE_OF_CHARGE,
    BATTERY_STATE_OF_HEALTH,
    RECORDS_SEATING,
    USAGE_ADJUSTMENTS,
    USAGE_DISTANCE,
)

from homeassistant import config_entries
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BATTERY_ASSUMED_VOLTAGE, DOMAIN
from .coordinator import MyPermobilCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class PermobilRequiredKeysMixin:
    """Mixin for required keys."""

    value_fn: Callable[[Any], Any]


@dataclass
class PermobilSensorEntityDescription(
    SensorEntityDescription, PermobilRequiredKeysMixin
):
    """Describes Permobil sensor entity."""


SENSOR_DESCRIPTIONS: tuple[PermobilSensorEntityDescription, ...] = (
    PermobilSensorEntityDescription(
        # Current battery as a percentage
        value_fn=lambda data: data.battery[BATTERY_STATE_OF_CHARGE[0]],
        key="state_of_charge",
        translation_key="state_of_charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PermobilSensorEntityDescription(
        # Current battery health as a percentage of original capacity
        value_fn=lambda data: data.battery[BATTERY_STATE_OF_HEALTH[0]],
        key="state_of_health",
        translation_key="state_of_health",
        icon="mdi:battery-heart-variant",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PermobilSensorEntityDescription(
        # Time until fully charged (displays 0 if not charging)
        value_fn=lambda data: data.battery[BATTERY_CHARGE_TIME_LEFT[0]],
        key="charge_time_left",
        translation_key="charge_time_left",
        icon="mdi:battery-clock",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
    ),
    PermobilSensorEntityDescription(
        # Distance possible on current change (km)
        value_fn=lambda data: data.battery[BATTERY_DISTANCE_LEFT[0]],
        key="distance_left",
        translation_key="distance_left",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
    ),
    PermobilSensorEntityDescription(
        # Drive time possible on current charge
        value_fn=lambda data: data.battery[BATTERY_INDOOR_DRIVE_TIME[0]],
        key="indoor_drive_time",
        translation_key="indoor_drive_time",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
    ),
    PermobilSensorEntityDescription(
        # Watt hours the battery can store given battery health
        value_fn=lambda data: data.battery[BATTERY_MAX_AMPERE_HOURS[0]]
        * BATTERY_ASSUMED_VOLTAGE,
        key="max_watt_hours",
        translation_key="max_watt_hours",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PermobilSensorEntityDescription(
        # Current amount of watt hours in battery
        value_fn=lambda data: data.battery[BATTERY_AMPERE_HOURS_LEFT[0]]
        * BATTERY_ASSUMED_VOLTAGE,
        key="watt_hours_left",
        translation_key="watt_hours_left",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PermobilSensorEntityDescription(
        # Distance that can be traveled with full charge given battery health (km)
        value_fn=lambda data: data.battery[BATTERY_MAX_DISTANCE_LEFT[0]],
        key="max_distance_left",
        translation_key="max_distance_left",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
    ),
    PermobilSensorEntityDescription(
        # Distance traveled today monotonically increasing, resets every 24h (km)
        value_fn=lambda data: data.daily_usage[USAGE_DISTANCE[0]],
        key="usage_distance",
        translation_key="usage_distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    PermobilSensorEntityDescription(
        # Number of adjustments monotonically increasing, resets every 24h
        value_fn=lambda data: data.daily_usage[USAGE_ADJUSTMENTS[0]],
        key="usage_adjustments",
        translation_key="usage_adjustments",
        native_unit_of_measurement="adjustments",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    PermobilSensorEntityDescription(
        # Largest number of adjustemnts in a single 24h period, never resets
        value_fn=lambda data: data.records[RECORDS_SEATING[0]],
        key="record_adjustments",
        translation_key="record_adjustments",
        native_unit_of_measurement="adjustments",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create sensors from a config entry created in the integrations UI."""

    coordinator: MyPermobilCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        PermobilSensor(coordinator=coordinator, description=description)
        for description in SENSOR_DESCRIPTIONS
    )


class PermobilSensor(CoordinatorEntity[MyPermobilCoordinator], SensorEntity):
    """Representation of a Sensor.

    This implements the common functions of all sensors.
    """

    _attr_has_entity_name = True
    _attr_suggested_display_precision = 0
    entity_description: PermobilSensorEntityDescription
    _available = True

    def __init__(
        self,
        coordinator: MyPermobilCoordinator,
        description: PermobilSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator=coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.p_api.email}_{self.entity_description.key}"
        )

    @property
    def available(self) -> bool:
        """Return True if the sensor has value."""
        try:
            self.entity_description.value_fn(self.coordinator.data)
            return True
        except KeyError:
            return False

    @property
    def native_value(self) -> float | None:
        """Return the value of the sensor."""
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except KeyError:
            return None
