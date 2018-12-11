"""
Support for X10 lights.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.x10/
"""
import logging
from subprocess import check_output, CalledProcessError

import voluptuous as vol

from homeassistant.const import (CONF_NAME, CONF_ID, CONF_DEVICES)
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, Light, PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

SUPPORT_X10 = SUPPORT_BRIGHTNESS

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [
        {
            vol.Required(CONF_ID): cv.string,
            vol.Required(CONF_NAME): cv.string,
        }
    ]),
})


def x10_command(command):
    """Execute X10 command and check output."""
    return check_output(["heyu", command])


def get_unit_status(code):
    """Get on/off status for given unit."""
    output = check_output('heyu onstate ' + code, shell=True)
    return int(output.decode('utf-8')[0])


def get_raw_brightness(code):
    """Get current raw brightness for given unit."""
    output = check_output('heyu rawlevel ' + code, shell=True).rstrip()
    return int(output)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the x10 Light platform."""
    is_cm11a = True
    try:
        x10_command('info')
    except CalledProcessError as err:
        _LOGGER.info("Assuming that the device is CM17A: %s", err.output)
        is_cm11a = False

    add_entities(X10Light(light, is_cm11a) for light in config[CONF_DEVICES])


class X10Light(Light):
    """Representation of an X10 Light."""

    def __init__(self, light, is_cm11a):
        """Initialize an X10 Light."""
        self._name = light['name']
        self._id = light['id']
        self._brightness = 0
        self._state = False
        self._is_cm11a = is_cm11a
        self.update()

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def brightness(self):
        """Return the brightness of the light."""
        return self._brightness

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_X10

    def turn_on(self, **kwargs):
        """Instruct the light to change brightness or turn on."""
        if self._is_cm11a:
            if ATTR_BRIGHTNESS in kwargs:
                desired_brightness = (kwargs[ATTR_BRIGHTNESS] / 255 * 210)
                delta_brightness = (
                    desired_brightness - int(get_raw_brightness(self._id)))
                delta_step = (abs(delta_brightness / 10) + 1)
                if delta_brightness > 0:
                    x10_command(
                        'bright ' + self._id.ljust(len(self._id)+1) +
                        str(int(delta_step)))
                else:
                    x10_command(
                        'dim ' + self._id.ljust(len(self._id)+1) +
                        str(int(delta_step)))
            else:
                x10_command('on ' + self._id)
        else:
            x10_command('fon ' + self._id)
        self._brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        self._state = True

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        if self._is_cm11a:
            x10_command('off ' + self._id)
        else:
            x10_command('foff ' + self._id)
        self._state = False

    def update(self):
        """Fetch update state."""
        if self._is_cm11a:
            self._state = bool(get_unit_status(self._id))
            self._brightness = (get_raw_brightness(self._id) / 210 * 255)
        else:
            # Not supported on CM17A
            pass
