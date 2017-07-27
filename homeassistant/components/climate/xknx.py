"""
Support for KNX/IP climate devices via XKNX

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/climate.xknx/
"""
import asyncio
import xknx
import voluptuous as vol

from homeassistant.components.xknx import DATA_XKNX
from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateDevice
from homeassistant.const import CONF_NAME, TEMP_CELSIUS, ATTR_TEMPERATURE
import homeassistant.helpers.config_validation as cv

CONF_SETPOINT_ADDRESS = 'setpoint_address'
CONF_TEMPERATURE_ADDRESS = 'temperature_address'

DEFAULT_NAME = 'XKNX Climate'
DEPENDENCIES = ['xknx']

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_SETPOINT_ADDRESS): cv.string,
    vol.Required(CONF_TEMPERATURE_ADDRESS): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

@asyncio.coroutine
def async_setup_platform(hass, config, add_devices, \
        discovery_info=None):
    """Set up climate(s) for XKNX platform."""
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
    """Set up climates for XKNX platform configured within plattform."""
    entities = []
    for device in hass.data[DATA_XKNX].xknx.devices:
        if isinstance(device, xknx.Climate) and \
                not hasattr(device, "already_added_to_hass"):
            entities.append(XKNXClimate(hass, device))
    add_devices(entities)

@asyncio.coroutine
def add_devices_from_platform(hass, config, add_devices):
    """Set up climate for XKNX platform configured within plattform."""
    from xknx import Climate
    climate = Climate(hass.data[DATA_XKNX].xknx,
                      name= \
                          config.get(CONF_NAME),
                      group_address_temperature= \
                          config.get(CONF_TEMPERATURE_ADDRESS),
                      group_address_setpoint= \
                          config.get(CONF_SETPOINT_ADDRESS))
    climate.already_added_to_hass = True
    hass.data[DATA_XKNX].xknx.devices.add(climate)
    add_devices([XKNXClimate(hass, climate)])


class XKNXClimate(ClimateDevice):
    """Representation of a XKNX climate."""

    def __init__(self, hass, device):
        self.device = device
        self.hass = hass
        self.register_callbacks()

        self._unit_of_measurement = TEMP_CELSIUS
        self._away = False  # not yet supported
        self._is_fan_on = False  # not yet supported


    def register_callbacks(self):
        """Register callbacks to update hass after device was changed."""
        def after_update_callback(device):
            # pylint: disable=unused-argument
            self.update_ha()
        self.device.register_device_updated_cb(after_update_callback)

    def update_ha(self):
        self.hass.async_add_job(self.async_update_ha_state())

    @property
    def name(self):
        """Return the name of the XKNX device."""
        return self.device.name

    @property
    def should_poll(self):
        """No polling needed within XKNX."""
        return False

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.device.temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self.device.setpoint

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self.device.setpoint = temperature

        #TODO Sent to KNX bus

        self.update_ha()

    def set_operation_mode(self, operation_mode):
        """Set operation mode."""
        raise NotImplementedError()
