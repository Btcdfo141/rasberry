"""Component providing HA sensor support for Ring Door Bell/Chimes."""

from __future__ import annotations

from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from typing import Any

from ring_doorbell import (
    RingCapability,
    RingDevices,
    RingDoorBell,
    RingEventKind,
    RingGeneric,
    RingOther,
    RingStickUpCam,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, RING_DEVICES, RING_DEVICES_COORDINATOR
from .coordinator import RingDataCoordinator
from .entity import RingEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a sensor for a Ring device."""
    devices: RingDevices = hass.data[DOMAIN][config_entry.entry_id][RING_DEVICES]
    devices_coordinator: RingDataCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        RING_DEVICES_COORDINATOR
    ]

    entities = [
        RingSensor(device, devices_coordinator, description)
        for description in SENSOR_TYPES
        for device in devices.all_devices
        if description.exists_fn(device)
    ]

    async_add_entities(entities)


class RingSensor(RingEntity, SensorEntity):
    """A sensor implementation for Ring device."""

    entity_description: RingSensorEntityDescription

    def __init__(
        self,
        device: RingGeneric,
        coordinator: RingDataCoordinator,
        description: RingSensorEntityDescription,
    ) -> None:
        """Initialize a sensor for Ring device."""
        super().__init__(device, coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{device.id}-{description.key}"
        self._attr_entity_registry_enabled_default = (
            description.entity_registry_enabled_default
        )
        self._attr_native_value = self.entity_description.value_fn(self._device)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Call update method."""

        self._device = self._get_coordinator_data().get_device(
            self._device.device_api_id
        )
        # History values can drop off the last 10 events so only update
        # the value if it's not None
        if native_value := self.entity_description.value_fn(self._device):
            self._attr_native_value = native_value
        if self.entity_description.extra_state_attributes_fn and (
            extra_attrs := self.entity_description.extra_state_attributes_fn(
                self._device
            )
        ):
            self._attr_extra_state_attributes = extra_attrs
        super()._handle_coordinator_update()


def _get_last_event(
    history_data: list[dict[str, Any]], kind: RingEventKind | None
) -> dict[str, Any] | None:
    if not history_data:
        return None
    if kind is None:
        return history_data[0]
    for entry in history_data:
        if entry["kind"] == kind.value:
            return entry
    return None


def _get_last_event_attrs(
    history_data: list[dict[str, Any]], kind: RingEventKind | None
) -> dict[str, Any] | None:
    if last_event := _get_last_event(history_data, kind):
        return {
            "created_at": last_event.get("created_at"),
            "answered": last_event.get("answered"),
            "recording_status": last_event.get("recording", {}).get("status"),
            "category": last_event.get("kind"),
        }
    return None


@dataclass(frozen=True, kw_only=True)
class RingSensorEntityDescription(SensorEntityDescription):
    """Describes Ring sensor entity."""

    kind: RingEventKind | None = None
    value_fn: Callable[[RingGeneric], StateType]
    exists_fn: Callable[[RingGeneric], bool] = lambda _: True
    extra_state_attributes_fn: (
        Callable[[RingGeneric], MutableMapping[str, Any] | None] | None
    ) = None


@dataclass(frozen=True, kw_only=True)
class RingDoorbellSensorEntityDescription(RingSensorEntityDescription):
    """Describes Ring sensor entity."""

    exists_fn: Callable[[RingDoorBell], bool] = lambda device: isinstance(
        device, RingDoorBell
    )
    value_fn: Callable[[RingDoorBell], StateType]


@dataclass(frozen=True, kw_only=True)
class RingOtherSensorEntityDescription(RingSensorEntityDescription):
    """Describes Ring sensor entity."""

    exists_fn: Callable[[RingOther], bool] = lambda device: isinstance(
        device, RingOther
    )
    value_fn: Callable[[RingOther], StateType]


SENSOR_TYPES: tuple[RingSensorEntityDescription, ...] = (
    RingSensorEntityDescription(
        key="battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.battery_life,
        exists_fn=lambda device: device.family != "chimes",
    ),
    RingSensorEntityDescription(
        key="last_activity",
        translation_key="last_activity",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda device: last_event.get("created_at")
        if (last_event := _get_last_event(device.last_history, None))
        else None,
        extra_state_attributes_fn=lambda device: last_event_attrs
        if (last_event_attrs := _get_last_event_attrs(device.last_history, None))
        else None,
        exists_fn=lambda device: device.has_capability(RingCapability.HISTORY),
    ),
    RingSensorEntityDescription(
        key="last_ding",
        translation_key="last_ding",
        kind=RingEventKind.DING,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda device: last_event.get("created_at")
        if (last_event := _get_last_event(device.last_history, RingEventKind.DING))
        else None,
        extra_state_attributes_fn=lambda device: last_event_attrs
        if (
            last_event_attrs := _get_last_event_attrs(
                device.last_history, RingEventKind.DING
            )
        )
        else None,
        exists_fn=lambda device: device.has_capability(RingCapability.HISTORY),
    ),
    RingSensorEntityDescription(
        key="last_motion",
        translation_key="last_motion",
        kind=RingEventKind.MOTION,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda device: last_event.get("created_at")
        if (last_event := _get_last_event(device.last_history, RingEventKind.MOTION))
        else None,
        extra_state_attributes_fn=lambda device: last_event_attrs
        if (
            last_event_attrs := _get_last_event_attrs(
                device.last_history, RingEventKind.MOTION
            )
        )
        else None,
        exists_fn=lambda device: device.has_capability(RingCapability.HISTORY),
    ),
    RingDoorbellSensorEntityDescription(
        key="volume",
        translation_key="volume",
        value_fn=lambda device: device.volume,
        exists_fn=lambda device: isinstance(device, RingStickUpCam)
        or device.has_capability(RingCapability.VOLUME),
    ),
    RingOtherSensorEntityDescription(
        key="doorbell_volume",
        translation_key="doorbell_volume",
        value_fn=lambda device: device.doorbell_volume,
    ),
    RingOtherSensorEntityDescription(
        key="mic_volume",
        translation_key="mic_volume",
        value_fn=lambda device: device.mic_volume,
    ),
    RingOtherSensorEntityDescription(
        key="voice_volume",
        translation_key="voice_volume",
        value_fn=lambda device: device.voice_volume,
    ),
    RingSensorEntityDescription(
        key="wifi_signal_category",
        translation_key="wifi_signal_category",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda device: device.wifi_signal_category,
    ),
    RingSensorEntityDescription(
        key="wifi_signal_strength",
        translation_key="wifi_signal_strength",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda device: device.wifi_signal_strength,
    ),
)
