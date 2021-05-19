"""Support for Google Calendar event device sensors."""
from datetime import timedelta
import logging
import re
from typing import Dict, List, cast

from aiohttp import web

from homeassistant.components import http
from homeassistant.const import HTTP_BAD_REQUEST, STATE_OFF, STATE_ON
from homeassistant.helpers.config_validation import (  # noqa: F401
    PLATFORM_SCHEMA,
    PLATFORM_SCHEMA_BASE,
    time_period_str,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.template import DATE_STR_FORMAT
from homeassistant.util import dt

# mypy: allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

DOMAIN = "calendar"
ENTITY_ID_FORMAT = DOMAIN + ".{}"
SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup(hass, config):
    """Track states and offer events for calendars."""
    component = hass.data[DOMAIN] = EntityComponent(
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL
    )

    hass.http.register_view(CalendarListView(component))
    hass.http.register_view(CalendarEventView(component))

    hass.components.frontend.async_register_built_in_panel(
        "calendar", "calendar", "hass:calendar"
    )

    await component.async_setup(config)
    return True


async def async_setup_entry(hass, entry):
    """Set up a config entry."""
    return await hass.data[DOMAIN].async_setup_entry(entry)


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    return await hass.data[DOMAIN].async_unload_entry(entry)


def get_date(date):
    """Get the dateTime from date or dateTime as a local."""
    if "date" in date:
        return dt.start_of_local_day(
            dt.dt.datetime.combine(dt.parse_date(date["date"]), dt.dt.time.min)
        )
    return dt.as_local(dt.parse_datetime(date["dateTime"]))


def normalize_event(event):
    """Normalize a calendar event."""
    normalized_event = {}

    start = event.get("start")
    end = event.get("end")
    start = get_date(start) if start is not None else None
    end = get_date(end) if end is not None else None
    normalized_event["dt_start"] = start
    normalized_event["dt_end"] = end

    start = start.strftime(DATE_STR_FORMAT) if start is not None else None
    end = end.strftime(DATE_STR_FORMAT) if end is not None else None
    normalized_event["start"] = start
    normalized_event["end"] = end

    # cleanup the string so we don't have a bunch of double+ spaces
    summary = event.get("summary", "")
    normalized_event["message"] = re.sub("  +", "", summary).strip()
    normalized_event["location"] = event.get("location", "")
    normalized_event["description"] = event.get("description", "")
    normalized_event["all_day"] = "date" in event["start"]

    if "upcoming_events" in event:
        normalized_event["upcoming_events"] = event.get("upcoming_events", [])

    return normalized_event


def calculate_offset(event, offset):
    """Calculate event offset.

    Return the updated event with the offset_time included.
    """
    summary = event.get("summary", "")
    # check if we have an offset tag in the message
    # time is HH:MM or MM
    reg = f"{offset}([+-]?[0-9]{{0,2}}(:[0-9]{{0,2}})?)"
    search = re.search(reg, summary)
    if search and search.group(1):
        time = search.group(1)
        if ":" not in time:
            if time[0] == "+" or time[0] == "-":
                time = f"{time[0]}0:{time[1:]}"
            else:
                time = f"0:{time}"

        offset_time = time_period_str(time)
        summary = (summary[: search.start()] + summary[search.end() :]).strip()
        event["summary"] = summary
    else:
        offset_time = dt.dt.timedelta()  # default it

    event["offset_time"] = offset_time
    return event


def is_offset_reached(event):
    """Have we reached the offset time specified in the event title."""
    start = get_date(event["start"])
    if start is None or event["offset_time"] == dt.dt.timedelta():
        return False

    return start + event["offset_time"] <= dt.now(start.tzinfo)


def get_normalized_event(event):
    """Get a normalized calendar event."""
    event = normalize_event(event)

    normalized_event = {
        "message": event["message"],
        "all_day": event["all_day"],
        "start_time": event["start"],
        "end_time": event["end"],
        "location": event["location"],
        "description": event["description"],
    }
    if "upcoming_events" in event:
        normalized_event["upcoming_events"] = event["upcoming_events"]

    return normalized_event


class CalendarEventDevice(Entity):
    """A calendar event device."""

    @property
    def event(self):
        """Return the next upcoming event."""
        raise NotImplementedError()

    @property
    def state_attributes(self):
        """Return the entity state attributes."""
        event = self.event
        if event is None:
            return None

        return get_normalized_event(event)

    @property
    def state(self):
        """Return the state of the calendar event."""
        event = self.event
        if event is None:
            return STATE_OFF

        event = normalize_event(event)
        start = event["dt_start"]
        end = event["dt_end"]

        if start is None or end is None:
            return STATE_OFF

        now = dt.now()

        if start <= now < end:
            return STATE_ON

        return STATE_OFF

    async def async_get_events(self, hass, start_date, end_date):
        """Return calendar events within a datetime range."""
        raise NotImplementedError()


class CalendarEventView(http.HomeAssistantView):
    """View to retrieve calendar content."""

    url = "/api/calendars/{entity_id}"
    name = "api:calendars:calendar"

    def __init__(self, component: EntityComponent) -> None:
        """Initialize calendar view."""
        self.component = component

    async def get(self, request, entity_id):
        """Return calendar events."""
        entity = self.component.get_entity(entity_id)
        start = request.query.get("start")
        end = request.query.get("end")
        if None in (start, end, entity):
            return web.Response(status=HTTP_BAD_REQUEST)
        try:
            start_date = dt.parse_datetime(start)
            end_date = dt.parse_datetime(end)
        except (ValueError, AttributeError):
            return web.Response(status=HTTP_BAD_REQUEST)
        event_list = await entity.async_get_events(
            request.app["hass"], start_date, end_date
        )
        return self.json(event_list)


class CalendarListView(http.HomeAssistantView):
    """View to retrieve calendar list."""

    url = "/api/calendars"
    name = "api:calendars"

    def __init__(self, component: EntityComponent) -> None:
        """Initialize calendar view."""
        self.component = component

    async def get(self, request: web.Request) -> web.Response:
        """Retrieve calendar list."""
        hass = request.app["hass"]
        calendar_list: List[Dict[str, str]] = []

        for entity in self.component.entities:
            state = hass.states.get(entity.entity_id)
            calendar_list.append({"name": state.name, "entity_id": entity.entity_id})

        return self.json(sorted(calendar_list, key=lambda x: cast(str, x["name"])))
