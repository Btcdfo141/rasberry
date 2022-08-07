"""Support for RainMachine updates."""
from __future__ import annotations

from enum import Enum
from typing import Any

from regenmaschine.errors import RequestError

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RainMachineData, RainMachineEntity
from .const import DATA_MACHINE_FIRMWARE_UPDATE_STATUS, DOMAIN
from .model import RainMachineEntityDescription


class UpdateStates(Enum):
    """Define an enum for update states."""

    IDLE = 1
    CHECKING = 2
    DOWNLOADING = 3
    UPGRADING = 4
    ERROR = 5
    REBOOT = 6


UPDATE_STATE_MAP = {
    1: UpdateStates.IDLE,
    2: UpdateStates.CHECKING,
    3: UpdateStates.DOWNLOADING,
    4: UpdateStates.UPGRADING,
    5: UpdateStates.ERROR,
    6: UpdateStates.REBOOT,
}


UPDATE_DESCRIPTION = RainMachineEntityDescription(
    key="update",
    name="Firmware",
    api_category=DATA_MACHINE_FIRMWARE_UPDATE_STATUS,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up WLED update based on a config entry."""
    data: RainMachineData = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([RainMachineUpdateEntity(entry, data, UPDATE_DESCRIPTION)])


class RainMachineUpdateEntity(RainMachineEntity, UpdateEntity):
    """Define a RainMachine update entity."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.PROGRESS
        | UpdateEntityFeature.SPECIFIC_VERSION
    )

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install an update."""
        try:
            await self._data.controller.machine.update_firmware()
        except RequestError as err:
            raise HomeAssistantError(f"Error while updating firmware: {err}") from err

        await self.coordinator.async_refresh()

    @callback
    def update_from_latest_data(self) -> None:
        """Update the state."""
        if version := self._version_coordinator.data["swVer"]:
            self._attr_installed_version = version
        else:
            self._attr_installed_version = None

        if self.coordinator.data["update"]:
            data = self.coordinator.data
            self._attr_in_progress = UPDATE_STATE_MAP[data["updateStatus"]] in (
                UpdateStates.DOWNLOADING,
                UpdateStates.UPGRADING,
                UpdateStates.REBOOT,
            )
            self._attr_latest_version = data["packageDetails"]["newVersion"]
        else:
            self._attr_in_progress = False
            self._attr_latest_version = self._attr_installed_version
