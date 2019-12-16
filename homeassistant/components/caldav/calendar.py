"""Support for WebDav Calendar."""
import copy
from datetime import datetime, timedelta
import logging
import re

import caldav
import voluptuous as vol

from homeassistant.components.calendar import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    CalendarEventDevice,
    calculate_offset,
    get_date,
    is_offset_reached,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.util import Throttle, dt

_LOGGER = logging.getLogger(__name__)

CONF_CALENDARS = "calendars"
CONF_CUSTOM_CALENDARS = "custom_calendars"
CONF_CALENDAR = "calendar"
CONF_SEARCH = "search"
CONF_ALL_DAY = 'all_day'

OFFSET = "!!"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        # pylint: disable=no-value-for-parameter
        vol.Required(CONF_URL): vol.Url(),
        vol.Optional(CONF_CALENDARS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Inclusive(CONF_USERNAME, "authentication"): cv.string,
        vol.Inclusive(CONF_PASSWORD, "authentication"): cv.string,
        vol.Optional(CONF_CUSTOM_CALENDARS, default=[]): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required(CONF_CALENDAR): cv.string,
                        vol.Required(CONF_NAME): cv.string,
                        vol.Required(CONF_SEARCH): cv.string,
                        vol.Optional(CONF_ALL_DAY, default=True): cv.boolean
                    }
                )
            ],
        ),
        vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
    }
)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=15)


def setup_platform(hass, config, add_entities, disc_info=None):
    """Set up the WebDav Calendar platform."""
    url = config[CONF_URL]
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    client = caldav.DAVClient(
        url, None, username, password, ssl_verify_cert=config[CONF_VERIFY_SSL]
    )

    calendars = client.principal().calendars()

    calendar_devices = []
    for calendar in list(calendars):
        # If a calendar name was given in the configuration,
        # ignore all the others
        if config[CONF_CALENDARS] and calendar.name not in config[CONF_CALENDARS]:
            _LOGGER.debug("Ignoring calendar '%s'", calendar.name)
            continue

        # Create additional calendars based on custom filtering rules
        for cust_calendar in config[CONF_CUSTOM_CALENDARS]:
            # Check that the base calendar matches
            if cust_calendar[CONF_CALENDAR] != calendar.name:
                continue

            name = cust_calendar[CONF_NAME]
            device_id = "{} {}".format(
                cust_calendar[CONF_CALENDAR], cust_calendar[CONF_NAME]
            )
            entity_id = generate_entity_id(ENTITY_ID_FORMAT, device_id, hass=hass)
            calendar_devices.append(
                WebDavCalendarEventDevice(
                    name, calendar, entity_id, cust_calendar.get(CONF_ALL_DAY, True), cust_calendar[CONF_SEARCH]
                )
            )

        # Create a default calendar if there was no custom one
        if not config[CONF_CUSTOM_CALENDARS]:
            name = calendar.name
            device_id = calendar.name
            entity_id = generate_entity_id(ENTITY_ID_FORMAT, device_id, hass=hass)
            calendar_devices.append(
                WebDavCalendarEventDevice(name, calendar, entity_id)
            )

    add_entities(calendar_devices, True)


class WebDavCalendarEventDevice(CalendarEventDevice):
    """A device for getting the next Task from a WebDav Calendar."""

    def __init__(self, name, calendar, entity_id, all_day=False, search=None):
        """Create the WebDav Calendar Event Device."""
        self.data = WebDavCalendarData(calendar, all_day, search)
        self.entity_id = entity_id
        self._event = None
        self._name = name
        self._offset_reached = False

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        return {"offset_reached": self._offset_reached}

    @property
    def event(self):
        """Return the next upcoming event."""
        return self._event

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    async def async_get_events(self, hass, start_date, end_date):
        """Get all events in a specific time frame."""
        return await self.data.async_get_events(hass, start_date, end_date)

    def update(self):
        """Update event data."""
        self.data.update()
        event = copy.deepcopy(self.data.event)
        if event is None:
            self._event = event
            return
        event = calculate_offset(event, OFFSET)
        self._offset_reached = is_offset_reached(event)
        self._event = event


class WebDavCalendarData:
    """Class to utilize the calendar dav client object to get next event."""

    def __init__(self, calendar, include_all_day, search):
        """Set up how we are going to search the WebDav calendar."""
        self.calendar = calendar
        self.include_all_day = include_all_day
        self.search = search
        self.event = None

    async def async_get_events(self, hass, start_date, end_date):
        """Get all events in a specific time frame."""
        # Get event list from the current calendar
        vevent_list = await hass.async_add_job(
            self.calendar.date_search, start_date, end_date
        )
        event_list = []
        for event in vevent_list:
            vevent = event.instance.vevent
            uid = None
            if hasattr(vevent, "uid"):
                uid = vevent.uid.value
            data = {
                "uid": uid,
                "title": vevent.summary.value,
                "start": self.get_hass_date(vevent.dtstart.value),
                "end": self.get_hass_date(self.get_end_date(vevent)),
                "location": self.get_attr_value(vevent, "location"),
                "description": self.get_attr_value(vevent, "description"),
            }

            data["start"] = get_date(data["start"]).isoformat()
            data["end"] = get_date(data["end"]).isoformat()

            event_list.append(data)

        return event_list

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data."""
        # We have to retrieve the results for the whole day as the server
        # won't return events that have already started
        results = self.calendar.date_search(
            dt.start_of_local_day(), dt.start_of_local_day() + timedelta(days=1)
        )

        # dtstart can be a date or datetime depending if the event lasts a
        # whole day. Convert everything to datetime to be able to sort it
        results.sort(key=lambda x: self.to_datetime(x.instance.vevent.dtstart.value))

        vevent = next(
            (
                event.instance.vevent
                for event in results
                if (
                    self.is_matching(event.instance.vevent, self.search)
                    and (
                        not self.is_all_day(event.instance.vevent)
                        or self.include_all_day
                    )
                    and not self.is_over(event.instance.vevent)
                )
            ),
            None,
        )

        # If no matching event could be found
        if vevent is None:
            _LOGGER.debug(
                "No matching event found in the %d results for %s",
                len(results),
                self.calendar.name,
            )
            self.event = None
            return

        # Populate the entity attributes with the event values
        self.event = {
            "summary": vevent.summary.value,
            "start": self.get_hass_date(vevent.dtstart.value),
            "end": self.get_hass_date(self.get_end_date(vevent)),
            "location": self.get_attr_value(vevent, "location"),
            "description": self.get_attr_value(vevent, "description"),
        }

    @staticmethod
    def is_matching(vevent, search):
        """Return if the event matches the filter criteria."""
        if search is None:
            return True

        pattern = re.compile(search)
        return (
            hasattr(vevent, "summary")
            and pattern.match(vevent.summary.value)
            or hasattr(vevent, "location")
            and pattern.match(vevent.location.value)
            or hasattr(vevent, "description")
            and pattern.match(vevent.description.value)
        )

    @staticmethod
    def is_all_day(vevent):
        """Return if the event last the whole day."""
        return not isinstance(vevent.dtstart.value, datetime)

    @staticmethod
    def is_over(vevent):
        """Return if the event is over."""
        return dt.now() >= WebDavCalendarData.to_datetime(
            WebDavCalendarData.get_end_date(vevent)
        )

    @staticmethod
    def get_hass_date(obj):
        """Return if the event matches."""
        if isinstance(obj, datetime):
            return {"dateTime": obj.isoformat()}

        return {"date": obj.isoformat()}

    @staticmethod
    def to_datetime(obj):
        """Return a datetime."""
        if isinstance(obj, datetime):
            if obj.tzinfo is None:
                # floating value, not bound to any time zone in particular
                # represent same time regardless of which time zone is currently being observed
                return obj.replace(tzinfo=dt.DEFAULT_TIME_ZONE)
            return obj
        return dt.as_local(dt.dt.datetime.combine(obj, dt.dt.time.min))

    @staticmethod
    def get_attr_value(obj, attribute):
        """Return the value of the attribute if defined."""
        if hasattr(obj, attribute):
            return getattr(obj, attribute).value
        return None

    @staticmethod
    def get_end_date(obj):
        """Return the end datetime as determined by dtend or duration."""
        if hasattr(obj, "dtend"):
            enddate = obj.dtend.value

        elif hasattr(obj, "duration"):
            enddate = obj.dtstart.value + obj.duration.value

        else:
            enddate = obj.dtstart.value + timedelta(days=1)

        return enddate
