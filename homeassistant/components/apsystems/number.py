"""Control the desired output for the inverter."""

from __future__ import annotations

from aiohttp import client_exceptions

from homeassistant import config_entries
from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType

from . import ApsystemsConfigEntry, ApSystemsData
from .entity import ApsystemsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    config = config_entry.runtime_data

    numbers = [MaxPower(data=config, entry=config_entry)]

    add_entities(numbers, True)


class MaxPower(ApsystemsEntity, NumberEntity):
    """Set the max power for the inverter."""

    _attr_device_class = NumberDeviceClass.POWER
    _attr_available = False
    _attr_native_max_value = 800
    _attr_native_min_value = 30
    _attr_native_step = 1

    def __init__(self, data: ApSystemsData, entry: ApsystemsConfigEntry) -> None:
        """Initialize the number input."""
        super().__init__(data, entry)
        assert entry.unique_id
        self._state = None
        self._attr_name = "Max Power"
        self._attr_unique_id = f"{entry.unique_id}_max_power"
        self._attr_translation_key = "max_power"

    async def async_update(self) -> None:
        """Update data for the number."""
        try:
            self._attr_native_value = await self._api.get_max_power()
            self._attr_available = True
        except (TimeoutError, client_exceptions.ClientConnectionError):
            self._attr_available = False

    async def async_set_native_value(self, value: float) -> None:
        """Set the desired value."""
        try:
            await self._api.set_max_power(int(value))
            self._attr_available = True
        except (TimeoutError, client_exceptions.ClientConnectionError):
            self._attr_available = False
        await self.async_update()
