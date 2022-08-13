"""MicroBot class."""
from __future__ import annotations

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo

from .const import MANUFACTURER


class MicroBotEntity(PassiveBluetoothCoordinatorEntity):
    """Generic entity for all MicroBots."""

    def __init__(self, coordinator, config_entry):
        """Initialise the entity."""
        super().__init__(coordinator)
        self._address = self.coordinator.ble_device.address
        self._attr_name = "MicroBot Push"
        self._attr_device_info = DeviceInfo(
            connections={(dr.CONNECTION_BLUETOOTH, self._address)},
            manufacturer=MANUFACTURER,
            model="Push",
            name="MicroBot",
        )

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self._address
