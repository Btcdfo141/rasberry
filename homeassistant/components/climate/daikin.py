"""
Support for the Daikin HVAC.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/climate.daikin/
"""
import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.climate import (
    ClimateDevice,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_FAN_MODE,
    SUPPORT_OPERATION_MODE, SUPPORT_SWING_MODE,

    STATE_OFF,
    STATE_AUTO, STATE_HEAT, STATE_COOL, STATE_DRY, STATE_FAN_ONLY,

    ATTR_OPERATION_MODE, ATTR_FAN_MODE, ATTR_SWING_MODE,
    ATTR_CURRENT_TEMPERATURE, ATTR_TARGET_TEMP_STEP,
    PLATFORM_SCHEMA
)
from homeassistant.const import (
    CONF_HOST, CONF_NAME,
    TEMP_CELSIUS,
    ATTR_TEMPERATURE
)

from homeassistant.components.daikin import (
    daikin_api_setup,
    ATTR_TARGET_TEMPERATURE,
    ATTR_INSIDE_TEMPERATURE,
    ATTR_OUTSIDE_TEMPERATURE
)

REQUIREMENTS = ['pydaikin==0.4']

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE |
                 SUPPORT_FAN_MODE |
                 SUPPORT_OPERATION_MODE |
                 SUPPORT_SWING_MODE)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=None): cv.string,
})

HA_STATE_TO_DAIKIN = {
    STATE_FAN_ONLY: 'fan',
    STATE_DRY: 'dry',
    STATE_COOL: 'cool',
    STATE_HEAT: 'hot',
    STATE_AUTO: 'auto',
    STATE_OFF: 'off',
}

HA_ATTR_TO_DAIKIN = {
    ATTR_OPERATION_MODE: 'mode',
    ATTR_FAN_MODE: 'f_rate',
    ATTR_SWING_MODE: 'f_dir',
}


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Daikin HVAC platform."""
    if discovery_info is not None:
        host = discovery_info.get('ip')
        name = None
        _LOGGER.info("Discovered a Daikin AC on %s", host)
    else:
        host = config.get(CONF_HOST)
        name = config.get(CONF_NAME)
        _LOGGER.info("Added Daikin AC on %s", host)

    api = daikin_api_setup(hass, host, name)
    add_devices([DaikinClimate(api)], True)


class DaikinClimate(ClimateDevice):
    """Representation of a Daikin HVAC."""

    def __init__(self, api):
        """Initialize the climate device."""
        from pydaikin import appliance

        self._api = api

        self._list = {
            ATTR_OPERATION_MODE: list(
                map(str.title, set(HA_STATE_TO_DAIKIN.values()))
            ),
            ATTR_FAN_MODE: list(
                map(
                    str.title,
                    appliance.daikin_values(HA_ATTR_TO_DAIKIN[ATTR_FAN_MODE])
                )
            ),
            ATTR_SWING_MODE: list(
                map(
                    str.title,
                    appliance.daikin_values(HA_ATTR_TO_DAIKIN[ATTR_SWING_MODE])
                )
            ),
        }

    def get(self, key):
        """Retrieve device settings from API library cache."""
        value = None
        cast_to_float = False

        if key in [ATTR_TEMPERATURE, ATTR_INSIDE_TEMPERATURE,
                   ATTR_CURRENT_TEMPERATURE]:
            value = self._api.device.values.get('htemp')
            cast_to_float = True
        if key == ATTR_TARGET_TEMPERATURE:
            value = self._api.device.values.get('stemp')
            cast_to_float = True
        elif key == ATTR_OUTSIDE_TEMPERATURE:
            value = self._api.device.values.get('otemp')
            cast_to_float = True
        elif key == ATTR_FAN_MODE:
            value = self._api.device.represent('f_rate')[1].title()
        elif key == ATTR_SWING_MODE:
            value = self._api.device.represent('f_dir')[1].title()
        elif key == ATTR_TARGET_TEMP_STEP:
            return 1
        elif key == ATTR_OPERATION_MODE:
            import re

            # Daikin can return also internal states auto-1 or auto-7
            # and we need to translate them as AUTO
            value = re.sub(
                '[^a-z]',
                '',
                self._api.device.represent('mode')[1]
            ).title()

        if value is None:
            _LOGGER.warning("Invalid value requested for key %s", key)
        else:
            if value == "-" or value == "--":
                value = None
            elif cast_to_float:
                try:
                    value = float(value)
                except ValueError:
                    value = None

        return value

    def set(self, settings):
        """Set device settings using API."""
        values = {}

        for attr in [ATTR_TEMPERATURE, ATTR_FAN_MODE, ATTR_SWING_MODE,
                     ATTR_OPERATION_MODE]:
            if attr in settings and settings[attr] is not None:
                value = settings[attr]
                daikin_attr = HA_ATTR_TO_DAIKIN.get(attr)
                if daikin_attr is not None:
                    if value.title() in self._list[attr]:
                        values[daikin_attr] = value.lower()
                    else:
                        _LOGGER.error("Invalid value %s for %s", attr, value)

                # temperature
                elif attr == ATTR_TEMPERATURE:
                    try:
                        values['stemp'] = str(int(value))
                    except ValueError:
                        _LOGGER.error("Invalid temperature %s", value)

        if values:
            self._api.device.set(values)
            self._api.update(force_refresh=True)

    @property
    def unique_id(self):
        """Return the ID of this AC."""
        return "{}.{}".format(self.__class__, self._api.ip_address)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def name(self):
        """Return the name of the thermostat, if any."""
        return self._api.name

    @property
    def temperature_unit(self):
        """Return the unit of measurement which this thermostat uses."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.get(ATTR_CURRENT_TEMPERATURE)

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self.get(ATTR_TARGET_TEMPERATURE)

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self.get(ATTR_TARGET_TEMP_STEP)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        self.set(kwargs)

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        return self.get(ATTR_OPERATION_MODE)

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return self._list.get(ATTR_OPERATION_MODE)

    def set_operation_mode(self, operation_mode):
        """Set HVAC mode."""
        self.set({ATTR_OPERATION_MODE: operation_mode})

    @property
    def current_fan_mode(self):
        """Return the fan setting."""
        return self.get(ATTR_FAN_MODE)

    def set_fan_mode(self, fan):
        """Set fan mode."""
        self.set({ATTR_FAN_MODE: fan})

    @property
    def fan_list(self):
        """List of available fan modes."""
        return self._list.get(ATTR_FAN_MODE)

    @property
    def current_swing_mode(self):
        """Return the fan setting."""
        return self.get(ATTR_SWING_MODE)

    def set_swing_mode(self, swing_mode):
        """Set new target temperature."""
        self.set({ATTR_SWING_MODE: swing_mode})

    @property
    def swing_list(self):
        """List of available swing modes."""
        return self._list.get(ATTR_SWING_MODE)

    def update(self):
        """Retrieve latest state."""
        self._api.update()
