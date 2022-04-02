"""Support for the Airzone sensors."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from aioairzone.const import (
    AZD_AIR_DEMAND,
    AZD_ERRORS,
    AZD_FLOOR_DEMAND,
    AZD_NAME,
    AZD_POWER,
    AZD_PROBLEMS,
    AZD_SYSTEMS,
    AZD_ZONES,
)

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AirzoneSystemEntity, AirzoneZoneEntity
from .const import DOMAIN
from .coordinator import AirzoneUpdateCoordinator


@dataclass
class AirzoneBinarySensorEntityDescription(BinarySensorEntityDescription):
    """A class that describes airzone binary sensor entities."""

    attributes: dict[str, str] | None = None


SYSTEM_BINARY_SENSOR_TYPES: Final[tuple[AirzoneBinarySensorEntityDescription, ...]] = (
    AirzoneBinarySensorEntityDescription(
        device_class=BinarySensorDeviceClass.POWER,
        key=AZD_POWER,
        name="Power",
    ),
    AirzoneBinarySensorEntityDescription(
        attributes={
            "errors": AZD_ERRORS,
        },
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        key=AZD_PROBLEMS,
        name="Problem",
    ),
)

ZONE_BINARY_SENSOR_TYPES: Final[tuple[AirzoneBinarySensorEntityDescription, ...]] = (
    AirzoneBinarySensorEntityDescription(
        device_class=BinarySensorDeviceClass.RUNNING,
        key=AZD_AIR_DEMAND,
        name="Air Demand",
    ),
    AirzoneBinarySensorEntityDescription(
        device_class=BinarySensorDeviceClass.RUNNING,
        key=AZD_FLOOR_DEMAND,
        name="Floor Demand",
    ),
    AirzoneBinarySensorEntityDescription(
        attributes={
            "errors": AZD_ERRORS,
        },
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        key=AZD_PROBLEMS,
        name="Problem",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Airzone binary sensors from a config_entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    system_binary_sensors = []
    for system_id, system_data in coordinator.data[AZD_SYSTEMS].items():
        for description in SYSTEM_BINARY_SENSOR_TYPES:
            if description.key in system_data:
                system_binary_sensors.append(
                    AirzoneSystemBinarySensor(
                        coordinator,
                        description,
                        entry,
                        system_id,
                        system_data,
                    )
                )

    zone_binary_sensors = []
    for system_zone_id, zone_data in coordinator.data[AZD_ZONES].items():
        for description in ZONE_BINARY_SENSOR_TYPES:
            if description.key in zone_data:
                zone_binary_sensors.append(
                    AirzoneZoneBinarySensor(
                        coordinator,
                        description,
                        entry,
                        system_zone_id,
                        zone_data,
                    )
                )

    async_add_entities(system_binary_sensors)
    async_add_entities(zone_binary_sensors)


class AirzoneSystemBinarySensor(AirzoneSystemEntity, BinarySensorEntity):
    """Define an Airzone System sensor."""

    def __init__(
        self,
        coordinator: AirzoneUpdateCoordinator,
        description: AirzoneBinarySensorEntityDescription,
        entry: ConfigEntry,
        system_id: str,
        system_data: dict[str, Any],
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, system_data)
        self._attr_name = f"System {system_id} {description.name}"
        self._attr_unique_id = f"{entry.entry_id}_{system_id}_{description.key}"
        self.attributes = description.attributes
        self.entity_description = description

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return state attributes."""
        if not self.attributes:
            return None
        return {key: self.get_system_value(val) for key, val in self.attributes.items()}

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.get_system_value(self.entity_description.key)


class AirzoneZoneBinarySensor(AirzoneZoneEntity, BinarySensorEntity):
    """Define an Airzone Zone sensor."""

    def __init__(
        self,
        coordinator: AirzoneUpdateCoordinator,
        description: AirzoneBinarySensorEntityDescription,
        entry: ConfigEntry,
        system_zone_id: str,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, system_zone_id, zone_data)
        self._attr_name = f"{zone_data[AZD_NAME]} {description.name}"
        self._attr_unique_id = f"{entry.entry_id}_{system_zone_id}_{description.key}"
        self.attributes = description.attributes
        self.entity_description = description

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return state attributes."""
        if not self.attributes:
            return None
        return {key: self.get_zone_value(val) for key, val in self.attributes.items()}

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.get_zone_value(self.entity_description.key)
