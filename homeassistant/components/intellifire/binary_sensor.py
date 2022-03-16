"""Support for IntelliFire Binary Sensors."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from intellifire4py import IntellifirePollData

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IntellifireDataUpdateCoordinator
from .const import DOMAIN
from .entity import IntellifireEntity


@dataclass
class IntellifireBinarySensorRequiredKeysMixin:
    """Mixin for required keys."""

    value_fn: Callable[[IntellifirePollData], bool]


@dataclass
class IntellifireBinarySensorEntityDescription(
    BinarySensorEntityDescription, IntellifireBinarySensorRequiredKeysMixin
):
    """Describes a binary sensor entity."""


INTELLIFIRE_BINARY_SENSORS: tuple[IntellifireBinarySensorEntityDescription, ...] = (
    IntellifireBinarySensorEntityDescription(
        key="on_off",  # This is the sensor name
        name="Flame",  # This is the human readable name
        icon="mdi:fire",
        value_fn=lambda data: data.is_on,
    ),
    IntellifireBinarySensorEntityDescription(
        key="timer_on",
        name="Timer On",
        icon="mdi:camera-timer",
        value_fn=lambda data: data.timer_on,
    ),
    IntellifireBinarySensorEntityDescription(
        key="pilot_light_on",
        name="Pilot Light On",
        icon="mdi:fire-alert",
        value_fn=lambda data: data.pilot_on,
    ),
    IntellifireBinarySensorEntityDescription(
        key="thermostat_on",
        name="Thermostat On",
        icon="mdi:home-thermometer-outline",
        value_fn=lambda data: data.thermostat_on,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_pilot_flame",
        name="Pilot Flame Error",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_pilot_flame,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_flame",
        name="Flame Error",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_flame,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_fan_delay",
        name="Fan Delay Error",
        icon="mdi:fan-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_fan_delay,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_maintenance",
        name="Maintenance Error",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_maintenance,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_disabled",
        name="Disabled Error",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_disabled,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_fan",
        name="Fan Error",
        icon="mdi:fan-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_fan,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_lights",
        name="Lights Error",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_lights,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_accessory",
        name="Accessory Error",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_accessory,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_soft_lock_out",
        name="Soft Lock Out Error",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_soft_lock_out,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_ecm_offline",
        name="ECM Offline Error",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_ecm_offline,
    ),
    IntellifireBinarySensorEntityDescription(
        key="error_offline",
        name="Offline Error",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.error_offline,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a IntelliFire On/Off Sensor."""
    coordinator: IntellifireDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        IntellifireBinarySensor(coordinator=coordinator, description=description)
        for description in INTELLIFIRE_BINARY_SENSORS
    )


class IntellifireBinarySensor(IntellifireEntity, BinarySensorEntity):
    """Extends IntellifireEntity with Binary Sensor specific logic."""

    entity_description: IntellifireBinarySensorEntityDescription

    @property
    def is_on(self) -> bool:
        """Use this to get the correct value."""
        return self.entity_description.value_fn(self.coordinator.api.data)
