"""Creates the number entities for the mower."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import Any

from aioautomower.exceptions import ApiException
from aioautomower.model import MowerAttributes, WorkArea
from aioautomower.session import AutomowerSession

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AutomowerDataUpdateCoordinator
from .entity import AutomowerBaseEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class AutomowerNumberEntityDescription(NumberEntityDescription):
    """Describes Automower number entity."""

    exists_fn: Callable[[MowerAttributes], bool] = lambda _: True
    value_fn: Callable[[MowerAttributes], int]
    set_value_fn: Callable[[AutomowerSession, str, float], Awaitable[Any]]


NUMBER_TYPES: tuple[AutomowerNumberEntityDescription, ...] = (
    AutomowerNumberEntityDescription(
        key="cutting_height",
        translation_key="cutting_height",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
        native_min_value=1,
        native_max_value=9,
        exists_fn=lambda data: data.cutting_height is not None,
        value_fn=lambda data: data.cutting_height,
        set_value_fn=lambda session, mower_id, cheight: session.set_cutting_height(
            mower_id, int(cheight)
        ),
    ),
)


@dataclass(frozen=True, kw_only=True)
class AutomowerWorkAreaNumberEntityDescription(NumberEntityDescription):
    """Describes Automower number entity."""

    exists_fn: Callable[[MowerAttributes], bool] = lambda _: True
    value_fn: Callable[[WorkArea], int]
    set_value_fn: Callable[[AutomowerSession, str, float, WorkArea], Awaitable[Any]]


WORK_AREA_NUMBER_TYPES: tuple[AutomowerWorkAreaNumberEntityDescription, ...] = (
    AutomowerWorkAreaNumberEntityDescription(
        key="cutting_height_work_area",
        translation_key="cutting_height_work_area",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=100,
        exists_fn=lambda data: True,
        value_fn=lambda data: data.cutting_height,
        set_value_fn=(
            lambda session, mower_id, cheight, work_area: session.set_cutting_height(
                mower_id, int(cheight), work_area
            )
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up number platform."""
    coordinator: AutomowerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AutomowerNumberEntity(mower_id, coordinator, description)
        for mower_id in coordinator.data
        for description in NUMBER_TYPES
        if description.exists_fn(coordinator.data[mower_id])
    )
    async_add_entities(
        AutomowerWorkAreaNumberEntity(mower_id, coordinator, description, work_area)
        for mower_id in coordinator.data
        for description in WORK_AREA_NUMBER_TYPES
        for work_area in coordinator.data[mower_id].work_areas
    )


class AutomowerNumberEntity(AutomowerBaseEntity, NumberEntity):
    """Defining the AutomowerNumberEntity with AutomowerNumberEntityDescription."""

    entity_description: AutomowerNumberEntityDescription

    def __init__(
        self,
        mower_id: str,
        coordinator: AutomowerDataUpdateCoordinator,
        description: AutomowerNumberEntityDescription,
    ) -> None:
        """Set up AutomowerNumberEntity."""
        super().__init__(mower_id, coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{mower_id}_{description.key}"

    @property
    def native_value(self) -> float:
        """Return the state of the number."""
        return self.entity_description.value_fn(self.mower_attributes)

    async def async_set_native_value(self, value: float) -> None:
        """Change to new number value."""
        try:
            await self.entity_description.set_value_fn(
                self.coordinator.api, self.mower_id, value
            )
        except ApiException as exception:
            raise HomeAssistantError(
                f"Command couldn't be sent to the command queue: {exception}"
            ) from exception


class AutomowerWorkAreaNumberEntity(AutomowerBaseEntity, NumberEntity):
    """Defining the AutomowerNumberEntity with AutomowerNumberEntityDescription."""

    entity_description: AutomowerWorkAreaNumberEntityDescription

    def __init__(
        self,
        mower_id: str,
        coordinator: AutomowerDataUpdateCoordinator,
        description: AutomowerWorkAreaNumberEntityDescription,
        work_area: int,
    ) -> None:
        """Set up AutomowerNumberEntity."""
        super().__init__(mower_id, coordinator)
        self.entity_description = description
        self.work_area = work_area
        self._attr_unique_id = f"{mower_id}_{description.key}_{work_area}"
        self._attr_translation_placeholders = {
            "work_area": self.mower_attributes.work_areas[work_area].name
        }

    @property
    def native_value(self) -> float:
        """Return the state of the number."""
        return self.entity_description.value_fn(
            self.mower_attributes.work_areas[self.work_area]
        )

    async def async_set_native_value(self, value: float) -> None:
        """Change to new number value."""
        try:
            await self.entity_description.set_value_fn(  # type: ignore[call-arg, misc]
                self.coordinator.api, self.mower_id, value
            )
        except ApiException as exception:
            raise HomeAssistantError(
                f"Command couldn't be sent to the command queue: {exception}"
            ) from exception
