"""Platform for Kostal Plenticore select widgets."""
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DEVICE_DEFAULT_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .helper import Plenticore, SelectDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class PlenticoreRequiredKeysMixin:
    """A class that describes required properties for plenticore select entities."""

    module_id: str
    options: list
    is_on: str


@dataclass
class PlenticoreSelectEntityDescription(
    SelectEntityDescription, PlenticoreRequiredKeysMixin
):
    """A class that describes plenticore select entities."""


SELECT_SETTINGS_DATA = [
    PlenticoreSelectEntityDescription(
        module_id="devices:local",
        key="battery_charge",
        name="Battery Charging / Usage mode",
        options=[
            "None",
            "Battery:SmartBatteryControl:Enable",
            "Battery:TimeControl:Enable",
        ],
        is_on="1",
    )
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add kostal plenticore Select widget."""
    plenticore: Plenticore = hass.data[DOMAIN][entry.entry_id]

    available_settings_data = await plenticore.client.get_settings()
    select_data_update_coordinator = SelectDataUpdateCoordinator(
        hass,
        _LOGGER,
        "Settings Data",
        timedelta(seconds=30),
        plenticore,
    )

    entities = []
    for description in SELECT_SETTINGS_DATA:
        if description.module_id not in available_settings_data:
            continue
        needed_data_ids = {
            data_id for data_id in description.options if data_id != "None"
        }
        available_data_ids = {
            setting.id for setting in available_settings_data[description.module_id]
        }
        if not needed_data_ids <= available_data_ids:
            continue
        entities.append(
            PlenticoreDataSelect(
                select_data_update_coordinator,
                description,
                entry_id=entry.entry_id,
                platform_name=entry.title,
                device_class="kostal_plenticore__battery",
                current_option="None",
                device_info=plenticore.device_info,
            )
        )

    async_add_entities(entities)


class PlenticoreDataSelect(CoordinatorEntity, SelectEntity, ABC):
    """Representation of a Plenticore Select."""

    _attr_entity_category = EntityCategory.CONFIG
    entity_description: PlenticoreSelectEntityDescription

    def __init__(
        self,
        coordinator: SelectDataUpdateCoordinator,
        description: PlenticoreSelectEntityDescription,
        entry_id: str,
        platform_name: str,
        device_class: str | None,
        current_option: str | None,
        device_info: DeviceInfo,
    ) -> None:
        """Create a new Select Entity for Plenticore process data."""
        super().__init__(coordinator)
        self.entity_description = description
        self.entry_id = entry_id
        self.platform_name = platform_name
        self._attr_device_class = device_class
        self.module_id = description.module_id
        self.data_id = description.key
        self._attr_options = description.options
        self.all_options = description.options
        self._attr_current_option = current_option
        self._is_on = description.is_on
        self._device_info = device_info
        self._attr_name = description.name or DEVICE_DEFAULT_NAME
        self._attr_unique_id = f"{entry_id}_{description.module_id}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.module_id in self.coordinator.data
            and self.data_id in self.coordinator.data[self.module_id]
        )

    async def async_added_to_hass(self) -> None:
        """Register this entity on the Update Coordinator."""
        await super().async_added_to_hass()
        self.coordinator.start_fetch_data(
            self.module_id, self.data_id, self.all_options
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister this entity from the Update Coordinator."""
        self.coordinator.stop_fetch_data(self.module_id, self.data_id, self.all_options)
        await super().async_will_remove_from_hass()

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        self._attr_current_option = option
        for all_option in self._attr_options:
            if all_option != "None":
                await self.coordinator.async_write_data(
                    self.module_id, {all_option: "0"}
                )
        if option != "None":
            await self.coordinator.async_write_data(self.module_id, {option: "1"})
        self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        if self.available:
            return self.coordinator.data[self.module_id][self.data_id]

        return None
