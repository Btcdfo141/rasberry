"""
Support for KNX/IP sensors via XKNX

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.xknx/
"""
import asyncio
import xknx
import voluptuous as vol

from homeassistant.components.xknx import DATA_XKNX
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv

CONF_ADDRESS = 'address'
CONF_VALUE_TYPE = 'value_type'

DEFAULT_NAME = 'XKNX Sensor'
DEPENDENCIES = ['xknx']

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ADDRESS): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_VALUE_TYPE): cv.string,
})

@asyncio.coroutine
def async_setup_platform(hass, config, add_devices, \
        discovery_info=None):
    """Set up sensor(s) for XKNX platform."""
    if DATA_XKNX not in hass.data \
            or not hass.data[DATA_XKNX].initialized:
        return False

    if discovery_info is not None:
        yield from add_devices_from_component(hass, add_devices)
    else:
        yield from add_devices_from_platform(hass, config, add_devices)

    return True

@asyncio.coroutine
def add_devices_from_component(hass, add_devices):
    """Set up sensors for XKNX platform configured via xknx.yaml."""
    entities = []
    for device in hass.data[DATA_XKNX].xknx.devices:
        if isinstance(device, xknx.devices.Sensor) and \
				not hasattr(device, "already_added_to_hass"):
            entities.append(XKNXSensor(hass, device))
    add_devices(entities)

@asyncio.coroutine
def add_devices_from_platform(hass, config, add_devices):
    """Set up sensor for XKNX platform configured within plattform."""
    sensor = xknx.devices.Sensor(
        hass.data[DATA_XKNX].xknx,
        name=config.get(CONF_NAME),
        group_address=config.get(CONF_ADDRESS),
        value_type=config.get(CONF_VALUE_TYPE))
    sensor.already_added_to_hass = True
    hass.data[DATA_XKNX].xknx.devices.add(sensor)
    add_devices([XKNXSensor(hass, sensor)])


class XKNXSensor(Entity):
    """Representation of a XKNX sensor."""

    def __init__(self, hass, device):
        self.device = device
        self.hass = hass
        self.register_callbacks()

    def register_callbacks(self):
        """Register callbacks to update hass after device was changed."""
        @asyncio.coroutine
        def after_update_callback(device):
            """Callback after device was updated."""
            # pylint: disable=unused-argument
            yield from self.async_update_ha_state()
        self.device.register_device_updated_cb(after_update_callback)

    @property
    def name(self):
        """Return the name of the XKNX device."""
        return self.device.name

    @property
    def should_poll(self):
        """No polling needed within XKNX."""
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.device.resolve_state()

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self.device.unit_of_measurement()

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return None
