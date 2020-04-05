"""Provides a sensor for Home Connect.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/integrations/sensor.homeconnect/
"""

from datetime import timedelta
import logging

from homeassistant.const import DEVICE_CLASS_TIMESTAMP
import homeassistant.util.dt as dt_util

from .api import HomeConnectEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Home Connect sensor."""

    def get_entities():
        """Get a list of entities."""
        entities = []
        hc_api = hass.data[DOMAIN][config_entry.entry_id]
        for device_dict in hc_api.devices:
            entity_dicts = device_dict.get("entities", {}).get("sensor", [])
            entity_list = [HomeConnectSensor(**d) for d in entity_dicts]
            device = device_dict["device"]
            device.entities += entity_list
            entities += entity_list
        return entities

    async_add_entities(await hass.async_add_executor_job(get_entities), True)


class HomeConnectSensor(HomeConnectEntity):
    """Sensor class for Home Connect."""

    def __init__(self, device, name, key, unit, icon, device_class, sign=1):
        """Initialize the entity."""
        super().__init__(device, name)
        self._state = None
        self._key = key
        self._unit = unit
        self._icon = icon
        self._device_class = device_class
        self._sign = sign

    @property
    def state(self):
        """Return true if the binary sensor is on."""
        return self._state

    @property
    def available(self):
        """Return true if the sensor is available."""
        return self._state is not None

    def update(self):
        """Update the sensos status."""
        status = self.device.appliance.status
        if self._key not in status:
            self._state = None
        else:
            if self.device_class == DEVICE_CLASS_TIMESTAMP:
                if "value" not in status[self._key]:
                    self._state = None
                else:
                    seconds = self._sign * float(status[self._key]["value"])
                    self._state = dt_util.utcnow() - timedelta(seconds=seconds)
            else:
                self._state = status[self._key].get("value", None)
        _LOGGER.debug("Updated, new state: %s", self._state)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class
