"""Sensor for monitoring the size of a file."""
import datetime
import logging
import os

from homeassistant.const import (
    CONF_FILE_PATH,
    CONF_UNIT_OF_MEASUREMENT,
    DATA_BYTES,
    DATA_MEGABYTES,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.reload import setup_reload_service
from homeassistant.util import slugify
import homeassistant.util.data_size as data_size

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:file"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the file size sensor."""

    setup_reload_service(hass, DOMAIN, PLATFORMS)

    file_path = config.get(CONF_FILE_PATH)
    if not hass.config.is_allowed_path(file_path):
        _LOGGER.error(
            "Path %s is not valid or allowed. Check directory whitelisting.",
            file_path,
        )
    else:
        add_entities(
            [Filesize(file_path, config.get(CONF_UNIT_OF_MEASUREMENT, DATA_MEGABYTES))],
            True,
        )


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the filesize sensor."""
    sensors = []

    sensors.append(
        Filesize(
            config_entry.data[CONF_FILE_PATH],
            config_entry.data[CONF_UNIT_OF_MEASUREMENT],
        )
    )

    async_add_entities(sensors, True)


class Filesize(Entity):
    """Encapsulates file size information."""

    def __init__(self, path, unit_of_measurement):
        """Initialize the data object."""
        self._path = path
        self._size = None
        self._last_updated = None
        filename = path.split("/")[-1]
        self._name = f"{filename} ({unit_of_measurement})"
        self._unit_of_measurement = unit_of_measurement
        self._unique_id = f"{path}_{unit_of_measurement}"
        self.entity_id = f"{DOMAIN}.{slugify(path)}_{unit_of_measurement}"

    def update(self):
        """Update the sensor."""
        statinfo = os.stat(self._path)
        self._size = statinfo.st_size
        last_updated = datetime.datetime.fromtimestamp(statinfo.st_mtime)
        self._last_updated = last_updated.isoformat()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def state(self):
        """Return the size of the file."""
        return round(
            data_size.convert(self._size, DATA_BYTES, self._unit_of_measurement), 2
        )

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return ICON

    @property
    def device_state_attributes(self):
        """Return other details about the sensor state."""
        return {
            "path": self._path,
            "last_updated": self._last_updated,
            "bytes": self._size,
        }

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement
