"""Doorsensor Support for the Nuki Lock."""
from __future__ import annotations

from pynuki.constants import STATE_DOORSENSOR_OPENED
from pynuki.device import NukiDevice

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NukiEntity, NukiEntryData
from .const import ATTR_NUKI_ID, ATTR_RING_TIMESTAMP, DOMAIN as NUKI_DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Nuki binary sensors."""
    entry_data: NukiEntryData = hass.data[NUKI_DOMAIN][entry.entry_id]

    lock_entities = []
    opener_entities = []

    for lock in entry_data.locks:
        if lock.is_door_sensor_activated:
            lock_entities.extend([NukiDoorsensorEntity(entry_data.coordinator, lock)])

    async_add_entities(lock_entities)

    for opener in entry_data.openers:
        opener_entities.extend([NukiRingactionEntity(entry_data.coordinator, opener)])

    async_add_entities(opener_entities)


class NukiDoorsensorEntity(NukiEntity[NukiDevice], BinarySensorEntity):
    """Representation of a Nuki Lock Doorsensor."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = BinarySensorDeviceClass.DOOR

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._nuki_device.nuki_id}_doorsensor"

    @property
    def extra_state_attributes(self):
        """Return the device specific state attributes."""
        data = {
            ATTR_NUKI_ID: self._nuki_device.nuki_id,
        }
        return data

    @property
    def available(self) -> bool:
        """Return true if door sensor is present and activated."""
        return super().available and self._nuki_device.is_door_sensor_activated

    @property
    def door_sensor_state(self):
        """Return the state of the door sensor."""
        return self._nuki_device.door_sensor_state

    @property
    def door_sensor_state_name(self):
        """Return the state name of the door sensor."""
        return self._nuki_device.door_sensor_state_name

    @property
    def is_on(self):
        """Return true if the door is open."""
        return self.door_sensor_state == STATE_DOORSENSOR_OPENED


class NukiRingactionEntity(NukiEntity[NukiDevice], BinarySensorEntity):
    """Representation of a Nuki Opener Ringaction."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:bell-ring"

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._nuki_device.nuki_id}_ringaction"

    @property
    def extra_state_attributes(self):
        """Return the device specific state attributes."""
        data = {
            ATTR_NUKI_ID: self._nuki_device.nuki_id,
            ATTR_RING_TIMESTAMP: self._nuki_device.ring_action_timestamp,
        }
        return data

    @property
    def ring_action_state(self):
        """Return the state of the ring action."""
        return self._nuki_device.ring_action_state

    @property
    def is_on(self) -> bool:
        """Return the value of the ring action state."""
        return self.ring_action_state
