"""Support for tracking the online status of a UPS."""
from __future__ import annotations

import logging
from typing import Final

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, APCUPSdCoordinator

_LOGGER = logging.getLogger(__name__)
_DESCRIPTION = BinarySensorEntityDescription(
    key="statflag",
    name="UPS Online Status",
    icon="mdi:heart",
)
_VALUE_ONLINE: Final = 8


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up an APCUPSd Online Status binary sensor."""
    coordinator: APCUPSdCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Do not create the binary sensor if APCUPSd does not provide STATFLAG field for us
    # to determine the online status.
    if _DESCRIPTION.key.upper() not in coordinator.data:
        return

    async_add_entities(
        [OnlineStatus(coordinator, _DESCRIPTION)],
        update_before_add=True,
    )


class OnlineStatus(CoordinatorEntity[APCUPSdCoordinator], BinarySensorEntity):
    """Representation of a UPS online status."""

    def __init__(
        self,
        coordinator: APCUPSdCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the APCUPSd binary device."""
        super().__init__(coordinator, context=description.key.upper())

        # Set up unique id and device info if serial number is available.
        if (serial_no := coordinator.ups_serial_no) is not None:
            self._attr_unique_id = f"{serial_no}_{description.key}"
        self._attr_device_info = coordinator.device_info

        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the UPS online."""
        key = self.entity_description.key.upper()
        # Check if _VALUE_ONLINE bit is set in STATFLAG.
        return int(self.coordinator.data[key], 16) & _VALUE_ONLINE > 0
