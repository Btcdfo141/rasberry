"""Base Entity for Ecoforest."""
from __future__ import annotations

from pyecoforest.models.device import Device

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import EcoforestCoordinator


class EcoforestEntity(CoordinatorEntity[EcoforestCoordinator]):
    """Common Ecoforest entity using CoordinatorEntity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcoforestCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize device information."""
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{self.entity_description.key}"
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.host)},
            name=MANUFACTURER,
            model=self.coordinator.data.model_name,
            sw_version=self.coordinator.data.firmware,
            manufacturer=MANUFACTURER,
        )

    @property
    def data(self) -> Device:
        """Return ecoforest data."""
        assert self.coordinator.data is not None
        return self.coordinator.data
