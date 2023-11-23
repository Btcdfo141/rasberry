"""Holiday Calendar."""
from __future__ import annotations

from datetime import datetime

from holidays import HolidayBase, country_holidays

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_COUNTRY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONF_PROVINCE, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Holiday Calendar config entry."""
    country: str = config_entry.data[CONF_COUNTRY]
    province: str | None = config_entry.data.get(CONF_PROVINCE)

    obj_holidays = country_holidays(country, subdiv=province)
    available_languages = [
        lang.replace("en_US", "en") for lang in obj_holidays.supported_languages
    ]

    if hass.config.language in available_languages:
        default_language = hass.config.language
    else:
        default_language = obj_holidays.default_language or "en_US"

    if default_language == "en" and country != "CA":
        default_language = "en_US"

    obj_holidays.update(
        dict(
            country_holidays(
                country,
                subdiv=province,
                language=default_language,
                years=dt_util.now().year,
            )
        )
    )

    async_add_entities(
        [
            HolidayCalendarEntity(
                config_entry.title,
                country,
                province,
                default_language,
                obj_holidays,
                config_entry.entry_id,
            )
        ],
        True,
    )


class HolidayCalendarEntity(CalendarEntity):
    """Representation of a Holiday Calendar element."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        name: str,
        country: str,
        province: str | None,
        default_language: str,
        obj_holidays: HolidayBase,
        unique_id: str,
    ) -> None:
        """Initialize HolidayCalendarEntity."""
        self._country = country
        self._province = province
        self._location = name
        self._default_language = default_language
        self._event: CalendarEvent | None = None
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name=name,
        )
        self._obj_holidays = obj_holidays

    @property
    def event(self) -> CalendarEvent:
        """Return the next upcoming event."""
        next_holiday = None
        for holiday_date, holiday_name in sorted(
            self._obj_holidays.items(), key=lambda x: x[0]
        ):
            if holiday_date >= dt_util.now().date():
                next_holiday = (holiday_date, holiday_name)
                break

        if next_holiday is None:
            self._obj_holidays.update(
                dict(
                    country_holidays(
                        self._country,
                        subdiv=self._province,
                        language=self._default_language,
                        years=dt_util.now().year + 1,
                    )
                )
            )

            for holiday_date, holiday_name in sorted(
                self._obj_holidays.items(), key=lambda x: x[0]
            ):
                if holiday_date >= dt_util.now().date():
                    next_holiday = (holiday_date, holiday_name)
                    break

        assert next_holiday is not None

        return CalendarEvent(
            summary=next_holiday[1],
            start=next_holiday[0],
            end=next_holiday[0],
            location=self._location,
        )

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        obj_holidays = dict(
            country_holidays(
                self._country,
                subdiv=self._province,
                years=list({start_date.year, end_date.year}),
                language=self._default_language,
            )
        )

        event_list: list[CalendarEvent] = []

        for holiday_date, holiday_name in obj_holidays.items():
            if start_date.date() <= holiday_date <= end_date.date():
                event = CalendarEvent(
                    summary=holiday_name,
                    start=holiday_date,
                    end=holiday_date,
                    location=self._location,
                )
                event_list.append(event)

        return event_list
