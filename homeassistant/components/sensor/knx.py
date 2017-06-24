"""
Sensors of a KNX Device.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/knx/
"""
import logging
import voluptuous as vol

from enum import Enum
from homeassistant.const import (
    CONF_NAME, CONF_MAXIMUM, CONF_MINIMUM,
    CONF_TYPE, TEMP_CELSIUS
)
from homeassistant.components.knx import (KNXConfig, KNXGroupAddress)
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['knx']

DEFAULT_NAME = "KNX sensor"

CONF_TEMPERATURE = 'temperature'
CONF_ADDRESS = 'address'
CONF_ILLUMINANCE = 'illuminance'
CONF_PERCENTAGE = 'percentage'
CONF_SPEED_MS = 'speed_ms'

KNXAddressType = Enum('KNXAddressType', 'float percent')

# define the fixed settings required for each sensor type
FIXED_SETTINGS_MAP = {
    #  Temperature as defined in KNX Standard 3.10 - 9.001 DPT_Value_Temp
    CONF_TEMPERATURE: {
        'unit': TEMP_CELSIUS,
        'default_minimum': -273,
        'default_maximum': 670760,
        'address_type': KNXAddressType.float
    },
    #  Speed m/s as defined in KNX Standard 3.10 - 9.005 DPT_Value_Wsp
    CONF_SPEED_MS: {
        'unit': 'm/s',
        'default_minimum': 0,
        'default_maximum': 670760,
        'address_type': KNXAddressType.float
    },
    #  Luminance(LUX) as defined in KNX Standard 3.10 - 9.004 DPT_Value_Lux
    CONF_ILLUMINANCE: {
        'unit': 'lx',
        'default_minimum': 0,
        'default_maximum': 670760,
        'address_type': KNXAddressType.float
    },
    #  Percentage(%) as defined in KNX Standard 3.10 - 5.001 DPT_Scaling
    CONF_PERCENTAGE: {
        'unit': '%',
        'default_minimum': 0,
        'default_maximum': 100,
        'address_type': KNXAddressType.percent
    }
}

SENSOR_TYPES = set(FIXED_SETTINGS_MAP.keys())

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_TYPE): vol.In(SENSOR_TYPES),
    vol.Required(CONF_ADDRESS): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MINIMUM): vol.Coerce(float),
    vol.Optional(CONF_MAXIMUM): vol.Coerce(float)
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the KNX Sensor platform."""
    add_devices([KNXSensor(hass, KNXConfig(config))])


class KNXSensor(KNXGroupAddress):
    """Representation of a KNX Sensor device."""

    def __init__(self, hass, config):
        """Initialize a KNX Float Sensor."""
        # set up the KNX Group address
        KNXGroupAddress.__init__(self, hass, config)

        device_type = config.config.get(CONF_TYPE)
        sensor_config = FIXED_SETTINGS_MAP.get(device_type)

        if not sensor_config:
            raise NotImplementedError()

        # set up the conversion function based on the address type
        address_type = sensor_config.get('address_type')
        if address_type == KNXAddressType.float:
            self.convert = self.convert_float
        elif address_type == KNXAddressType.percent:
            self.convert = self.convert_percent
        else:
            raise NotImplementedError()

        # other settings
        self._unit_of_measurement = sensor_config.get('unit')
        default_min = float(sensor_config.get('default_minimum'))
        default_max = float(sensor_config.get('default_maximum'))
        self._minimum_value = config.config.get(CONF_MINIMUM, default_min)
        self._maximum_value = config.config.get(CONF_MAXIMUM, default_max)
        _LOGGER.debug(
            "%s: configured additional settings: unit=%s, "
            "min=%f, max=%f, type=%s",
            self.name, self._unit_of_measurement,
            self._minimum_value, self._maximum_value, str(address_type)
        )

        self._value = None

    @property
    def state(self):
        """Return the Value of the KNX Sensor."""
        return self._value

    @property
    def unit_of_measurement(self):
        """Return the defined Unit of Measurement for the KNX Sensor."""
        return self._unit_of_measurement

    def update(self):
        """Update KNX sensor."""
        super().update()

        self._value = None

        if self._data:
            if self._data == 0:
                value = 0
            else:
                value = self.convert(self._data)
            if self._minimum_value <= value <= self._maximum_value:
                self._value = value

    @property
    def cache(self):
        """We don't want to cache any Sensor Value."""
        return False

    def convert_float(self, raw_value):
        """Conversion for 2 byte floating point values.

        2byte Floating Point KNX Telegram.
        Defined in KNX 3.7.2 - 3.10
        """
        from knxip.conversion import knx2_to_float

        return knx2_to_float(raw_value)

    def convert_percent(self, raw_value):
        """Conversion for scaled byte values.

        1byte percentage scaled KNX Telegram.
        Defined in KNX 3.7.2 - 3.10.
        """
        summed_value = 0
        try:
            # convert raw value in bytes
            for val in raw_value:
                summed_value *= 256
                summed_value += val
        except TypeError:
            # pknx returns a non-iterable type for unsuccessful reads
            pass

        return round(summed_value * 100 / 255)
