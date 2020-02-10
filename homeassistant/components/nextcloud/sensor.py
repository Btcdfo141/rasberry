"""Summary data from Nextcoud."""
from datetime import timedelta
import logging

from nextcloudmonitor import NextcloudMonitor
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_time_interval

_LOGGER = logging.getLogger(__name__)

# Assign domain
DOMAIN = "nextcloud"
# Set Default scan interval in seconds
SCAN_INTERVAL = timedelta(seconds=60)

# Validate user configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_URL): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None) -> None:
    """Set up the Nextcloud sensor."""
    # Fetch Nextcloud Monitor api data
    ncm = NextcloudMonitor(
        config[CONF_URL], config[CONF_USERNAME], config[CONF_PASSWORD]
    )
    hass.data[DOMAIN] = get_sensors(ncm.data)

    def nextcloud_update(event_time):
        """Update data from nextcloud api."""
        ncm.update()
        hass.data[DOMAIN] = get_sensors(ncm.data)

    # Update sensors on time interval
    track_time_interval(hass, nextcloud_update, config[CONF_SCAN_INTERVAL])

    # Setup sensors
    sensors = []
    for name, _ in hass.data[DOMAIN].items():
        sensors.append(NextcloudSensor(name))
    add_entities(sensors, True)


# Use recursion to create list of sensors & values based on nextcloud api data
def get_sensors(api_data):
    """Use Recursion to discover sensors and values."""
    result = {}
    for key, value in api_data.items():
        if isinstance(value, dict):
            result.update(get_sensors(value))
        else:
            result[key] = value
    return result


class NextcloudSensor(Entity):
    """Represents a Nextcloud sensor."""

    def __init__(self, item):
        """Initialize the Nextcloud sensor."""
        self.item = item
        self.value = None

    @property
    def icon(self):
        """Return the icon for this sensor."""
        return "mdi:cloud"

    @property
    def name(self):
        """Return the name for this sensor."""
        return f"{DOMAIN}_{self.item}"

    @property
    def state(self):
        """Return the state for this sensor."""
        return self.value

    @property
    def unique_id(self):
        """Return the unique ID for this sensor."""
        return f"{DOMAIN}_{self.name}"

    def update(self):
        """Update the sensor."""
        self.value = self.hass.data[DOMAIN][self.item]
