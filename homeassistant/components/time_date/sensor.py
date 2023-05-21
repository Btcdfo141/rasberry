"""Support for showing the date and the time."""
from __future__ import annotations

from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    SensorEntity,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import homeassistant.util.dt as dt_util

from .const import CONF_DISPLAY_OPTIONS, DOMAIN, OPTION_TYPES, TIME_STR_FORMAT

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_DISPLAY_OPTIONS, default=["time"]): vol.All(
            cv.ensure_list, [vol.In(OPTION_TYPES)]
        )
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Time & Date sensor."""
    async_create_issue(
        hass,
        DOMAIN,
        "deprecated_yaml",
        breaks_in_ha_version="2023.9.0",
        is_fixable=False,
        severity=IssueSeverity.WARNING,
        translation_key="deprecated_yaml",
    )

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config,
        )
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Time & Date sensor."""
    entities = []
    for option_type in OPTION_TYPES:
        status = option_type in entry.data.get(CONF_DISPLAY_OPTIONS, OPTION_TYPES)
        entities.append(TimeDateSensor(hass, option_type, status, entry.entry_id))
    async_add_entities(entities)


class TimeDateSensor(SensorEntity):
    """Implementation of a Time and Date sensor."""

    _attr_has_entity_name = True

    def __init__(self, hass, option_type, status, entry_id):
        """Initialize the sensor."""
        self._attr_name = OPTION_TYPES[option_type]
        self._attr_unique_id = f"{option_type}_{entry_id}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry_id)},
            name="Time & Date",
        )
        self._attr_entity_registry_enabled_default = status
        self.entity_id = ENTITY_ID_FORMAT.format(option_type)
        self.type = option_type
        self._state = None
        self.hass = hass
        self.unsub = None

        self._update_internal_state(dt_util.utcnow())

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if "date" in self.type and "time" in self.type:
            return "mdi:calendar-clock"
        if "date" in self.type:
            return "mdi:calendar"
        return "mdi:clock"

    async def async_added_to_hass(self) -> None:
        """Set up first update."""
        self.unsub = async_track_point_in_utc_time(
            self.hass, self.point_in_time_listener, self.get_next_interval()
        )

    async def async_will_remove_from_hass(self) -> None:
        """Cancel next update."""
        if self.unsub:
            self.unsub()
            self.unsub = None

    def get_next_interval(self):
        """Compute next time an update should occur."""
        now = dt_util.utcnow()

        if self.type == "date":
            tomorrow = dt_util.as_local(now) + timedelta(days=1)
            return dt_util.start_of_local_day(tomorrow)

        if self.type == "beat":
            # Add 1 hour because @0 beats is at 23:00:00 UTC.
            timestamp = dt_util.as_timestamp(now + timedelta(hours=1))
            interval = 86.4
        else:
            timestamp = dt_util.as_timestamp(now)
            interval = 60

        delta = interval - (timestamp % interval)
        next_interval = now + timedelta(seconds=delta)
        _LOGGER.debug("%s + %s -> %s (%s)", now, delta, next_interval, self.type)

        return next_interval

    def _update_internal_state(self, time_date):
        time = dt_util.as_local(time_date).strftime(TIME_STR_FORMAT)
        time_utc = time_date.strftime(TIME_STR_FORMAT)
        date = dt_util.as_local(time_date).date().isoformat()
        date_utc = time_date.date().isoformat()

        if self.type == "time":
            self._state = time
        elif self.type == "date":
            self._state = date
        elif self.type == "date_time":
            self._state = f"{date}, {time}"
        elif self.type == "date_time_utc":
            self._state = f"{date_utc}, {time_utc}"
        elif self.type == "time_date":
            self._state = f"{time}, {date}"
        elif self.type == "time_utc":
            self._state = time_utc
        elif self.type == "beat":
            # Calculate Swatch Internet Time.
            time_bmt = time_date + timedelta(hours=1)
            delta = timedelta(
                hours=time_bmt.hour,
                minutes=time_bmt.minute,
                seconds=time_bmt.second,
                microseconds=time_bmt.microsecond,
            )

            # Use integers to better handle rounding. For example,
            # int(63763.2/86.4) = 737 but 637632//864 = 738.
            beat = int(delta.total_seconds() * 10) // 864

            self._state = f"@{beat:03d}"
        elif self.type == "date_time_iso":
            self._state = dt_util.parse_datetime(f"{date} {time}").isoformat()

    @callback
    def point_in_time_listener(self, time_date):
        """Get the latest data and update state."""
        self._update_internal_state(time_date)
        self.async_write_ha_state()
        self.unsub = async_track_point_in_utc_time(
            self.hass, self.point_in_time_listener, self.get_next_interval()
        )
