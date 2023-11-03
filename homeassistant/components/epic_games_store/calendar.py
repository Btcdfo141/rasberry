"""Calendar platform for a Epic Games Store."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CalendarType, EGSCalendarUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the local calendar platform."""
    coordinator: EGSCalendarUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        EGSCalendar(coordinator, entry.entry_id, CalendarType.FREE),
        EGSCalendar(coordinator, entry.entry_id, CalendarType.DISCOUNT),
    ]
    async_add_entities(entities, True)


class EGSCalendar(CoordinatorEntity[EGSCalendarUpdateCoordinator], CalendarEntity):
    """A calendar entity by Epic Games Store."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EGSCalendarUpdateCoordinator,
        config_entry_id: str,
        cal_type: CalendarType,
    ) -> None:
        """Initialize EGSCalendar."""
        super().__init__(coordinator)
        self._cal_type = cal_type
        self._attr_translation_key = f"{self._cal_type}_games"
        self._attr_unique_id = f"{config_entry_id}-{self._cal_type}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, config_entry_id)},
            manufacturer="Epic Games Store",
            name="Epic Games Store",
        )
        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._event

    @property  # type: ignore[misc]
    def state_attributes(self) -> dict[str, Any] | None:
        """Return the entity state attributes."""
        return {
            **(super().state_attributes or {}),
            "games": self.coordinator.data[self._cal_type],
        }

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        events: list[dict[str, Any]] = self.coordinator.data[self._cal_type]
        return [_get_calendar_event(event) for event in events]

    async def async_update(self) -> None:
        """Update entity state with the next upcoming event."""
        event: list[dict[str, Any]] = self.coordinator.data[self._cal_type]
        if event:
            self._event = _get_calendar_event(event[0])


def _get_calendar_event(event: dict[str, Any]) -> CalendarEvent:
    """Return a CalendarEvent from an API event."""
    return CalendarEvent(
        summary=event["title"],
        start=event["discount_start_at"],
        end=event["discount_end_at"],
        description=f"{event['description']}\n\n{event['url']}",
    )
