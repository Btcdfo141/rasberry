"""
This platform provides binary sensors for OpenUV data.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.openuv/
"""
import logging

from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.const import CONF_MONITORED_CONDITIONS
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.openuv import (
    BINARY_SENSORS, DATA_PROTECTION_WINDOW, DOMAIN, TOPIC_UPDATE,
    TYPE_PROTECTION_WINDOW, OpenUvEntity)
from homeassistant.util.dt import as_local, parse_datetime, utcnow

DEPENDENCIES = ['openuv']
_LOGGER = logging.getLogger(__name__)

ATTR_PROTECTION_WINDOW_STARTING_TIME = 'start_time'
ATTR_PROTECTION_WINDOW_STARTING_UV = 'start_uv'
ATTR_PROTECTION_WINDOW_ENDING_TIME = 'end_time'
ATTR_PROTECTION_WINDOW_ENDING_UV = 'end_uv'


async def async_setup_platform(
        hass, config, async_add_devices, discovery_info=None):
    """Set up the OpenUV binary sensor platform."""
    if discovery_info is None:
        return

    openuv = hass.data[DOMAIN]

    binary_sensors = []
    for sensor_type in discovery_info[CONF_MONITORED_CONDITIONS]:
        name, icon = BINARY_SENSORS[sensor_type]
        binary_sensors.append(
            OpenUvBinarySensor(openuv, sensor_type, name, icon))

    async_add_devices(binary_sensors, True)


class OpenUvBinarySensor(OpenUvEntity, BinarySensorDevice):
    """Define a binary sensor for OpenUV."""

    def __init__(self, openuv, sensor_type, name, icon):
        """Initialize the sensor."""
        super().__init__(openuv)

        self._icon = icon
        self._latitude = openuv.client.latitude
        self._longitude = openuv.client.longitude
        self._name = name
        self._sensor_type = sensor_type
        self._state = None

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

    @property
    def is_on(self):
        """Return the status of the sensor."""
        return self._state

    @property
    def should_poll(self):
        """Disable polling."""
        return False

    @property
    def unique_id(self) -> str:
        """Return a unique, HASS-friendly identifier for this entity."""
        return '{0}_{1}_{2}'.format(
            self._latitude, self._longitude, self._sensor_type)

    @callback
    def _update_data(self):
        """Update the state."""
        self.async_schedule_update_ha_state(True)

    async def async_added_to_hass(self):
        """Register callbacks."""
        async_dispatcher_connect(
            self.hass, TOPIC_UPDATE, self._update_data)

    async def async_update(self):
        """Update the state."""
        data = self.openuv.data[DATA_PROTECTION_WINDOW]['result']
        if self._sensor_type == TYPE_PROTECTION_WINDOW:
            self._state = parse_datetime(
                data['from_time']) <= utcnow() <= parse_datetime(
                    data['to_time'])
            self._attrs.update({
                ATTR_PROTECTION_WINDOW_ENDING_TIME:
                    as_local(parse_datetime(data['to_time'])),
                ATTR_PROTECTION_WINDOW_ENDING_UV: data['to_uv'],
                ATTR_PROTECTION_WINDOW_STARTING_UV: data['from_uv'],
                ATTR_PROTECTION_WINDOW_STARTING_TIME:
                    as_local(parse_datetime(data['from_time'])),
            })
