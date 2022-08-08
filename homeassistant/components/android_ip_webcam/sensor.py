"""Support for Android IP Webcam sensors."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydroid_ipcam import PyDroidIPCam

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .coordinator import AndroidIPCamDataUpdateCoordinator
from .entity import AndroidIPCamBaseEntity


@dataclass
class AndroidIPWebcamSensorEntityDescriptionMixin:
    """Mixin for required keys."""

    value_fn: Callable[[PyDroidIPCam], tuple[StateType, str | None]]


@dataclass
class AndroidIPWebcamSensorEntityDescription(
    SensorEntityDescription, AndroidIPWebcamSensorEntityDescriptionMixin
):
    """Entity description class for Android IP Webcam sensors."""

    unit_fn: Callable[[PyDroidIPCam], tuple[StateType, str | None]] = lambda _: (
        None,
        None,
    )


SENSOR_TYPES: tuple[AndroidIPWebcamSensorEntityDescription, ...] = (
    AndroidIPWebcamSensorEntityDescription(
        key="audio_connections",
        name="Audio Connections",
        icon="mdi:speaker",
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ipcam: ipcam.status_data.get("audio_connections"),
    ),
    AndroidIPWebcamSensorEntityDescription(
        key="battery_level",
        name="Battery Level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ipcam: ipcam.export_sensor("battery_level"),
        unit_fn=lambda ipcam: ipcam.export_sensor("battery_level"),
    ),
    AndroidIPWebcamSensorEntityDescription(
        key="battery_temp",
        name="Battery Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ipcam: ipcam.export_sensor("battery_temp"),
        unit_fn=lambda ipcam: ipcam.export_sensor("battery_temp"),
    ),
    AndroidIPWebcamSensorEntityDescription(
        key="battery_voltage",
        name="Battery Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ipcam: ipcam.export_sensor("battery_voltage"),
        unit_fn=lambda ipcam: ipcam.export_sensor("battery_voltage"),
    ),
    AndroidIPWebcamSensorEntityDescription(
        key="light",
        name="Light Level",
        icon="mdi:flashlight",
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ipcam: ipcam.export_sensor("light"),
        unit_fn=lambda ipcam: ipcam.export_sensor("light"),
    ),
    AndroidIPWebcamSensorEntityDescription(
        key="motion",
        name="Motion",
        icon="mdi:run",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ipcam: ipcam.export_sensor("motion"),
        unit_fn=lambda ipcam: ipcam.export_sensor("motion"),
    ),
    AndroidIPWebcamSensorEntityDescription(
        key="pressure",
        name="Pressure",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ipcam: ipcam.export_sensor("pressure"),
        unit_fn=lambda ipcam: ipcam.export_sensor("pressure"),
    ),
    AndroidIPWebcamSensorEntityDescription(
        key="proximity",
        name="Proximity",
        icon="mdi:map-marker-radius",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ipcam: ipcam.export_sensor("proximity"),
        unit_fn=lambda ipcam: ipcam.export_sensor("proximity"),
    ),
    AndroidIPWebcamSensorEntityDescription(
        key="sound",
        name="Sound",
        icon="mdi:speaker",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ipcam: ipcam.export_sensor("sound"),
        unit_fn=lambda ipcam: ipcam.export_sensor("sound"),
    ),
    AndroidIPWebcamSensorEntityDescription(
        key="video_connections",
        name="Video Connections",
        icon="mdi:eye",
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda ipcam: ipcam.status_data.get("video_connections"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IP Webcam sensors from config entry."""

    coordinator: AndroidIPCamDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]
    sensor_types = [
        sensor
        for sensor in SENSOR_TYPES
        if sensor.key
        in coordinator.ipcam.enabled_sensors
        + ["audio_connections", "video_connections"]
    ]
    async_add_entities(
        [IPWebcamSensor(coordinator, description) for description in sensor_types]
    )


class IPWebcamSensor(AndroidIPCamBaseEntity, SensorEntity):
    """Representation of a IP Webcam sensor."""

    entity_description: AndroidIPWebcamSensorEntityDescription

    def __init__(
        self,
        coordinator: AndroidIPCamDataUpdateCoordinator,
        description: AndroidIPWebcamSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{description.key}"
        self.entity_description = description
        super().__init__(coordinator)

    @property
    def native_value(self) -> StateType:
        """Return native value of sensor."""
        value, _ = self.entity_description.value_fn(self.entity_description.key)
        return value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return native unit of measurement of sensor."""
        _, unit = self.entity_description.unit_fn(self.entity_description.key)
        return unit
