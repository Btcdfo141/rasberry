"""Support for Nightscout sensors."""
from asyncio import TimeoutError as AsyncIOTimeoutError
from datetime import timedelta
import hashlib
import logging
from typing import Callable, List

from aiohttp import ClientError
from py_nightscout import Api as NightscoutAPI
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_RESOURCE
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

from .const import ATTR_DATE, ATTR_DELTA, ATTR_DEVICE, ATTR_DIRECTION, ATTR_SVG, DOMAIN

SCAN_INTERVAL = timedelta(minutes=1)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Blood Glucose"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Exclusive(CONF_RESOURCE, CONF_RESOURCE): cv.url,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

PLATFORM_SCHEMA = vol.All(PLATFORM_SCHEMA)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Callable[[List[Entity], bool], None],
) -> None:
    """Set up the Glucose Sensor."""
    api = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NightscoutSensor(api, "Blood Sugar")], True)


class NightscoutSensor(Entity):
    """Implementation of a Nightscout sensor."""

    def __init__(self, api: NightscoutAPI, name):
        """Initialize the Nightscout sensor."""
        self.api = api
        self._unique_id = hashlib.sha256(api.server_url.encode("utf-8")).hexdigest()
        self._name = name
        self._state = None
        self._attributes = None
        self._unit_of_measurement = "mg/dL"
        self._icon = "mdi:cloud-question"
        self._available = False

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def available(self):
        """Return if the sensor data are available."""
        return self._available

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return self._icon

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    async def async_update(self):
        """Fetch the latest data from Nightscout REST API and update the state."""
        try:
            values = await self.api.get_sgvs()
        except (ClientError, AsyncIOTimeoutError, OSError) as error:
            _LOGGER.error("Error fetching data. Failed with %s", error)
            self._available = False
            return

        self._available = True
        self._attributes = {}
        self._state = None
        if values:
            value = values[0]
            self._attributes = {
                ATTR_DEVICE: value.device,
                ATTR_DATE: value.date,
                ATTR_SVG: value.sgv,
                ATTR_DELTA: value.delta,
                ATTR_DIRECTION: value.direction,
            }
            self._state = value.sgv
            self._icon = self._parse_icon()
        else:
            self._available = False
            _LOGGER.warning("Empty reply found when expecting JSON data")

    def _parse_icon(self) -> str:
        """Update the icon based on the direction attribute."""
        switcher = {
            "Flat": "mdi:arrow-right",
            "SingleDown": "mdi:arrow-down",
            "FortyFiveDown": "mdi:arrow-bottom-right",
            "DoubleDown": "mdi:chevron-triple-down",
            "SingleUp": "mdi:arrow-up",
            "FortyFiveUp": "mdi:arrow-top-right",
            "DoubleUp": "mdi:chevron-triple-up",
        }
        return switcher.get(self._attributes[ATTR_DIRECTION], "mdi:cloud-question")

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes
