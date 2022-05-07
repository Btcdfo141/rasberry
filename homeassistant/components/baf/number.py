"""Support for Big Ass Fans number."""
from __future__ import annotations

from typing import cast

from aiobafi6 import Device

from homeassistant import config_entries
from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import BAFEntity
from .models import BAFData

FAN_NUMBER_DESCRIPTIONS = (
    NumberEntityDescription(
        key="return_to_auto_timeout",
        name="Return to Auto Timeout",
        min_value=60,
        max_value=43200,
    ),
    NumberEntityDescription(
        key="motion_sense_timeout",
        name="Motion Sense Timeout",
        min_value=60,
        max_value=864000,
    ),
    NumberEntityDescription(
        key="comfort_min_speed",
        name="Comfort Minimum Speed",
        min_value=0,
        max_value=7,
    ),
    NumberEntityDescription(
        key="comfort_max_speed",
        name="Comfort Maximum Speed",
        min_value=0,
        max_value=7,
    ),
    NumberEntityDescription(
        key="comfort_heat_assist_speed",
        name="Comfort Heat Assist Speed",
        min_value=1,
        max_value=7,
    ),
)

LIGHT_NUMBER_DESCRIPTIONS = (
    NumberEntityDescription(
        key="light_return_to_auto_timeout",
        name="Light Return to Auto Timeout",
        min_value=60,
        max_value=43200,
    ),
    NumberEntityDescription(
        key="light_auto_motion_timeout",
        name="Light Motion Sense Timeout",
        min_value=60,
        max_value=864000,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BAF numbers."""
    data: BAFData = hass.data[DOMAIN][entry.entry_id]
    device = data.device
    descriptions: list[NumberEntityDescription] = []
    if device.has_fan:
        descriptions.extend(FAN_NUMBER_DESCRIPTIONS)
    if device.has_light:
        descriptions.extend(LIGHT_NUMBER_DESCRIPTIONS)
    async_add_entities(BAFNumber(device, description) for description in descriptions)


class BAFNumber(BAFEntity, NumberEntity):
    """BAF number."""

    entity_description: NumberEntityDescription

    def __init__(self, device: Device, description: NumberEntityDescription) -> None:
        """Initialize the entity."""
        self.entity_description = description
        super().__init__(device, f"{device.name} {description.name}")
        self._attr_unique_id = f"{self._device.mac_address}-{description.key}"

    @callback
    def _async_update_attrs(self) -> None:
        """Update attrs from device."""
        self._attr_value = cast(
            float, getattr(self._device, self.entity_description.key)
        )

    async def async_set_value(self, value: float) -> None:
        """Set the value."""
        setattr(self._device, self.entity_description.key, int(value))
