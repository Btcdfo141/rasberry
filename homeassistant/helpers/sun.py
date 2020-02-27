"""Helpers for sun events."""
import datetime
from typing import TYPE_CHECKING, Optional, Tuple, Union

from homeassistant.const import SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET
from homeassistant.core import callback
from homeassistant.loader import bind_hass
from homeassistant.util import dt as dt_util

from .typing import HomeAssistantType

if TYPE_CHECKING:
    import astral  # pylint: disable=unused-import

DATA_LOCATION_CACHE = "astral_location_cache"

ELEVATION_AGNOSTIC_EVENTS = ("noon", "midnight")


@callback
@bind_hass
def get_astral_location(
    hass: HomeAssistantType,
) -> Tuple["astral.location.Location", "astral.Elevation"]:
    """Get an astral location for the current Home Assistant configuration."""
    from astral import LocationInfo  # pylint: disable=import-outside-toplevel
    from astral.location import Location  # pylint: disable=import-outside-toplevel

    timezone = str(hass.config.time_zone)
    latitude = hass.config.latitude
    longitude = hass.config.longitude
    elevation = hass.config.elevation
    info = ("", "", timezone, latitude, longitude)

    # Cache astral locations so they aren't recreated with the same args
    if DATA_LOCATION_CACHE not in hass.data:
        hass.data[DATA_LOCATION_CACHE] = {}

    if info not in hass.data[DATA_LOCATION_CACHE]:
        hass.data[DATA_LOCATION_CACHE][info] = Location(LocationInfo(*info))

    return hass.data[DATA_LOCATION_CACHE][info], elevation


@callback
@bind_hass
def get_astral_event_next(
    hass: HomeAssistantType,
    event: str,
    utc_point_in_time: Optional[datetime.datetime] = None,
    offset: Optional[datetime.timedelta] = None,
) -> datetime.datetime:
    """Calculate the next specified solar event."""
    location, elevation = get_astral_location(hass)
    return get_location_astral_event_next(
        location, elevation, event, utc_point_in_time, offset
    )


@callback
def get_location_astral_event_next(
    location: "astral.location.Location",
    elevation: "astral.Elevation",
    event: str,
    utc_point_in_time: Optional[datetime.datetime] = None,
    offset: Optional[datetime.timedelta] = None,
) -> datetime.datetime:
    """Calculate the next specified solar event."""
    if offset is None:
        offset = datetime.timedelta()

    if utc_point_in_time is None:
        utc_point_in_time = dt_util.utcnow()

    kwargs = {"local": False}
    if event not in ELEVATION_AGNOSTIC_EVENTS:
        kwargs["observer_elevation"] = elevation

    mod = -1
    while True:
        try:
            next_dt: datetime.datetime = (
                getattr(location, event)(
                    dt_util.as_local(utc_point_in_time).date()
                    + datetime.timedelta(days=mod),
                    **kwargs,
                )
                + offset
            )
            if next_dt > utc_point_in_time:
                return next_dt
        except ValueError:
            pass
        mod += 1


@callback
@bind_hass
def get_astral_event_date(
    hass: HomeAssistantType,
    event: str,
    date: Union[datetime.date, datetime.datetime, None] = None,
) -> Optional[datetime.datetime]:
    """Calculate the astral event time for the specified date."""
    location, elevation = get_astral_location(hass)

    if date is None:
        date = dt_util.now().date()

    if isinstance(date, datetime.datetime):
        date = dt_util.as_local(date).date()

    kwargs = {"local": False}
    if event not in ELEVATION_AGNOSTIC_EVENTS:
        kwargs["observer_elevation"] = elevation

    try:
        return getattr(location, event)(date, **kwargs)  # type: ignore
    except ValueError:
        # Event never occurs for specified date.
        return None


@callback
@bind_hass
def is_up(
    hass: HomeAssistantType, utc_point_in_time: Optional[datetime.datetime] = None
) -> bool:
    """Calculate if the sun is currently up."""
    if utc_point_in_time is None:
        utc_point_in_time = dt_util.utcnow()

    next_sunrise = get_astral_event_next(hass, SUN_EVENT_SUNRISE, utc_point_in_time)
    next_sunset = get_astral_event_next(hass, SUN_EVENT_SUNSET, utc_point_in_time)

    return next_sunrise > next_sunset
