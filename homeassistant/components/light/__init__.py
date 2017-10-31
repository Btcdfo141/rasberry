"""
Provides functionality to interact with lights.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/light/
"""
import asyncio
from datetime import timedelta
import logging
import os
import csv

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.loader import bind_hass
from homeassistant.components import group
from homeassistant.config import load_yaml_config_file
from homeassistant.const import (
    STATE_ON, STATE_OFF, SERVICE_TURN_ON, SERVICE_TURN_OFF, SERVICE_TOGGLE,
    ATTR_ENTITY_ID, ATTR_STATE)
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA  # noqa
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import async_restore_state
import homeassistant.util.color as color_util

DOMAIN = "light"
DEPENDENCIES = ['group']
SCAN_INTERVAL = timedelta(seconds=30)

GROUP_NAME_ALL_LIGHTS = 'all lights'
ENTITY_ID_ALL_LIGHTS = group.ENTITY_ID_FORMAT.format('all_lights')

ENTITY_ID_FORMAT = DOMAIN + ".{}"

# Bitfield of features supported by the light entity
SUPPORT_BRIGHTNESS = 1
SUPPORT_COLOR_TEMP = 2
SUPPORT_EFFECT = 4
SUPPORT_FLASH = 8
SUPPORT_RGB_COLOR = 16
SUPPORT_TRANSITION = 32
SUPPORT_XY_COLOR = 64
SUPPORT_WHITE_VALUE = 128

# Integer that represents transition time in seconds to make change.
ATTR_TRANSITION = "transition"

# Lists holding color values
ATTR_RGB_COLOR = "rgb_color"
ATTR_XY_COLOR = "xy_color"
ATTR_COLOR_TEMP = "color_temp"
ATTR_KELVIN = "kelvin"
ATTR_MIN_MIREDS = "min_mireds"
ATTR_MAX_MIREDS = "max_mireds"
ATTR_COLOR_NAME = "color_name"
ATTR_WHITE_VALUE = "white_value"

# Brightness of the light, 0..255 or percentage
ATTR_BRIGHTNESS = "brightness"
ATTR_BRIGHTNESS_PCT = "brightness_pct"

# String representing a profile (built-in ones or external defined).
ATTR_PROFILE = "profile"

# If the light should flash, can be FLASH_SHORT or FLASH_LONG.
ATTR_FLASH = "flash"
FLASH_SHORT = "short"
FLASH_LONG = "long"

# List of possible effects
ATTR_EFFECT_LIST = "effect_list"

# Apply an effect to the light, can be EFFECT_COLORLOOP.
ATTR_EFFECT = "effect"
EFFECT_COLORLOOP = "colorloop"
EFFECT_RANDOM = "random"
EFFECT_WHITE = "white"

COLOR_GROUP = "Color descriptors"

LIGHT_PROFILES_FILE = "light_profiles.csv"

PROP_TO_ATTR = {
    'brightness': ATTR_BRIGHTNESS,
    'color_temp': ATTR_COLOR_TEMP,
    'min_mireds': ATTR_MIN_MIREDS,
    'max_mireds': ATTR_MAX_MIREDS,
    'rgb_color': ATTR_RGB_COLOR,
    'xy_color': ATTR_XY_COLOR,
    'white_value': ATTR_WHITE_VALUE,
    'effect_list': ATTR_EFFECT_LIST,
    'effect': ATTR_EFFECT,
}

# Service call validation schemas
VALID_TRANSITION = vol.All(vol.Coerce(float), vol.Clamp(min=0, max=6553))
VALID_BRIGHTNESS = vol.All(vol.Coerce(int), vol.Clamp(min=0, max=255))
VALID_BRIGHTNESS_PCT = vol.All(vol.Coerce(float), vol.Range(min=0, max=100))

LIGHT_TURN_ON_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.entity_ids,
    vol.Exclusive(ATTR_PROFILE, COLOR_GROUP): cv.string,
    ATTR_TRANSITION: VALID_TRANSITION,
    ATTR_BRIGHTNESS: VALID_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT: VALID_BRIGHTNESS_PCT,
    vol.Exclusive(ATTR_COLOR_NAME, COLOR_GROUP): cv.string,
    vol.Exclusive(ATTR_RGB_COLOR, COLOR_GROUP):
        vol.All(vol.ExactSequence((cv.byte, cv.byte, cv.byte)),
                vol.Coerce(tuple)),
    vol.Exclusive(ATTR_XY_COLOR, COLOR_GROUP):
        vol.All(vol.ExactSequence((cv.small_float, cv.small_float)),
                vol.Coerce(tuple)),
    vol.Exclusive(ATTR_COLOR_TEMP, COLOR_GROUP):
        vol.All(vol.Coerce(int), vol.Range(min=1)),
    vol.Exclusive(ATTR_KELVIN, COLOR_GROUP):
        vol.All(vol.Coerce(int), vol.Range(min=0)),
    ATTR_WHITE_VALUE: vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    ATTR_FLASH: vol.In([FLASH_SHORT, FLASH_LONG]),
    ATTR_EFFECT: cv.string,
})

LIGHT_TURN_OFF_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.entity_ids,
    ATTR_TRANSITION: VALID_TRANSITION,
    ATTR_FLASH: vol.In([FLASH_SHORT, FLASH_LONG]),
})

LIGHT_TOGGLE_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.entity_ids,
    ATTR_STATE: vol.In([STATE_ON, STATE_OFF]),
    ATTR_TRANSITION: VALID_TRANSITION,
})

PROFILE_SCHEMA = vol.Schema(
    vol.ExactSequence((str, cv.small_float, cv.small_float, cv.byte))
)

_LOGGER = logging.getLogger(__name__)


def extract_info(state):
    """Extract light parameters from a state object."""
    params = {key: state.attributes[key] for key in PROP_TO_ATTR
              if key in state.attributes}
    params['is_on'] = state.state == STATE_ON
    return params


@bind_hass
def is_on(hass, entity_id=None):
    """Return if the lights are on based on the statemachine."""
    entity_id = entity_id or ENTITY_ID_ALL_LIGHTS
    return hass.states.is_state(entity_id, STATE_ON)


@bind_hass
def turn_on(hass, entity_id=None, transition=None, brightness=None,
            brightness_pct=None, rgb_color=None, xy_color=None,
            color_temp=None, kelvin=None, white_value=None,
            profile=None, flash=None, effect=None, color_name=None):
    """Turn all or specified light on."""
    hass.add_job(
        async_turn_on, hass, entity_id, transition, brightness, brightness_pct,
        rgb_color, xy_color, color_temp, kelvin, white_value,
        profile, flash, effect, color_name)


@callback
@bind_hass
def async_turn_on(hass, entity_id=None, transition=None, brightness=None,
                  brightness_pct=None, rgb_color=None, xy_color=None,
                  color_temp=None, kelvin=None, white_value=None,
                  profile=None, flash=None, effect=None, color_name=None):
    """Turn all or specified light on."""
    data = {
        key: value for key, value in [
            (ATTR_ENTITY_ID, entity_id),
            (ATTR_PROFILE, profile),
            (ATTR_TRANSITION, transition),
            (ATTR_BRIGHTNESS, brightness),
            (ATTR_BRIGHTNESS_PCT, brightness_pct),
            (ATTR_RGB_COLOR, rgb_color),
            (ATTR_XY_COLOR, xy_color),
            (ATTR_COLOR_TEMP, color_temp),
            (ATTR_KELVIN, kelvin),
            (ATTR_WHITE_VALUE, white_value),
            (ATTR_FLASH, flash),
            (ATTR_EFFECT, effect),
            (ATTR_COLOR_NAME, color_name),
        ] if value is not None
    }

    hass.async_add_job(hass.services.async_call(DOMAIN, SERVICE_TURN_ON, data))


@bind_hass
def turn_off(hass, entity_id=None, transition=None):
    """Turn all or specified light off."""
    hass.add_job(async_turn_off, hass, entity_id, transition)


@callback
@bind_hass
def async_turn_off(hass, entity_id=None, transition=None):
    """Turn all or specified light off."""
    data = {
        key: value for key, value in [
            (ATTR_ENTITY_ID, entity_id),
            (ATTR_TRANSITION, transition),
        ] if value is not None
    }

    hass.async_add_job(hass.services.async_call(
        DOMAIN, SERVICE_TURN_OFF, data))


@bind_hass
def toggle(hass, entity_id=None, state=None, transition=None):
    """Toggle all or specified light."""
    data = {
        key: value for key, value in [
            (ATTR_ENTITY_ID, entity_id),
            (ATTR_STATE, state),
            (ATTR_TRANSITION, transition),
        ] if value is not None
    }

    hass.services.call(DOMAIN, SERVICE_TOGGLE, data)


def preprocess_turn_on_alternatives(params):
    """Processing extra data for turn light on request."""
    profile = Profiles.get(params.pop(ATTR_PROFILE, None))
    if profile is not None:
        params.setdefault(ATTR_XY_COLOR, profile[:2])
        params.setdefault(ATTR_BRIGHTNESS, profile[2])

    color_name = params.pop(ATTR_COLOR_NAME, None)
    if color_name is not None:
        params[ATTR_RGB_COLOR] = color_util.color_name_to_rgb(color_name)

    kelvin = params.pop(ATTR_KELVIN, None)
    if kelvin is not None:
        mired = color_util.color_temperature_kelvin_to_mired(kelvin)
        params[ATTR_COLOR_TEMP] = int(mired)

    brightness_pct = params.pop(ATTR_BRIGHTNESS_PCT, None)
    if brightness_pct is not None:
        params[ATTR_BRIGHTNESS] = int(255 * brightness_pct/100)


@asyncio.coroutine
def async_setup(hass, config):
    """Expose light control via statemachine and services."""
    component = EntityComponent(
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL, GROUP_NAME_ALL_LIGHTS)
    yield from component.async_setup(config)

    # load profiles from files
    profiles_valid = yield from Profiles.load_profiles(hass)
    if not profiles_valid:
        return False

    @asyncio.coroutine
    def async_handle_light_service(service):
        """Hande a turn light on or off service call."""
        # Get the validated data
        params = service.data.copy()

        # Convert the entity ids to valid light ids
        target_lights = component.async_extract_from_service(service)
        params.pop(ATTR_ENTITY_ID, None)

        preprocess_turn_on_alternatives(params)

        update_tasks = []
        for light in target_lights:
            if service.service == SERVICE_TURN_ON:
                yield from light.async_turn_on(**params)
            elif service.service == SERVICE_TURN_OFF:
                yield from light.async_turn_off(**params)
            else:
                yield from light.async_toggle(**params)

            if not light.should_poll:
                continue
            update_tasks.append(light.async_update_ha_state(True))

        if update_tasks:
            yield from asyncio.wait(update_tasks, loop=hass.loop)

    # Listen for light on and light off service calls.
    descriptions = yield from hass.async_add_job(
        load_yaml_config_file, os.path.join(
            os.path.dirname(__file__), 'services.yaml'))

    hass.services.async_register(
        DOMAIN, SERVICE_TURN_ON, async_handle_light_service,
        descriptions.get(SERVICE_TURN_ON), schema=LIGHT_TURN_ON_SCHEMA)

    hass.services.async_register(
        DOMAIN, SERVICE_TURN_OFF, async_handle_light_service,
        descriptions.get(SERVICE_TURN_OFF), schema=LIGHT_TURN_OFF_SCHEMA)

    hass.services.async_register(
        DOMAIN, SERVICE_TOGGLE, async_handle_light_service,
        descriptions.get(SERVICE_TOGGLE), schema=LIGHT_TOGGLE_SCHEMA)

    return True


class Profiles:
    """Representation of available color profiles."""

    _all = None

    @classmethod
    @asyncio.coroutine
    def load_profiles(cls, hass):
        """Load and cache profiles."""
        def load_profile_data(hass):
            """Load built-in profiles and custom profiles."""
            profile_paths = [os.path.join(os.path.dirname(__file__),
                                          LIGHT_PROFILES_FILE),
                             hass.config.path(LIGHT_PROFILES_FILE)]
            profiles = {}

            for profile_path in profile_paths:
                if not os.path.isfile(profile_path):
                    continue
                with open(profile_path) as inp:
                    reader = csv.reader(inp)

                    # Skip the header
                    next(reader, None)

                    try:
                        for rec in reader:
                            profile, color_x, color_y, brightness = \
                                PROFILE_SCHEMA(rec)
                            profiles[profile] = (color_x, color_y, brightness)
                    except vol.MultipleInvalid as ex:
                        _LOGGER.error(
                            "Error parsing light profile from %s: %s",
                            profile_path, ex)
                        return None
            return profiles

        cls._all = yield from hass.async_add_job(load_profile_data, hass)
        return cls._all is not None

    @classmethod
    def get(cls, name):
        """Return a named profile."""
        return cls._all.get(name)


class Light(ToggleEntity):
    """Representation of a light."""

    # pylint: disable=no-self-use

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return None

    @property
    def xy_color(self):
        """Return the XY color value [float, float]."""
        return None

    @property
    def rgb_color(self):
        """Return the RGB color value [int, int, int]."""
        return None

    @property
    def color_temp(self):
        """Return the CT color value in mireds."""
        return None

    @property
    def min_mireds(self):
        """Return the coldest color_temp that this light supports."""
        # Default to the Philips Hue value that HA has always assumed
        return 154

    @property
    def max_mireds(self):
        """Return the warmest color_temp that this light supports."""
        # Default to the Philips Hue value that HA has always assumed
        return 500

    @property
    def white_value(self):
        """Return the white value of this light between 0..255."""
        return None

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return None

    @property
    def effect(self):
        """Return the current effect."""
        return None

    @property
    def state_attributes(self):
        """Return optional state attributes."""
        data = {}

        if self.is_on:
            for prop, attr in PROP_TO_ATTR.items():
                value = getattr(self, prop)
                if value is not None:
                    data[attr] = value

            if ATTR_RGB_COLOR not in data and ATTR_XY_COLOR in data and \
               ATTR_BRIGHTNESS in data:
                data[ATTR_RGB_COLOR] = color_util.color_xy_brightness_to_RGB(
                    data[ATTR_XY_COLOR][0], data[ATTR_XY_COLOR][1],
                    data[ATTR_BRIGHTNESS])

        return data

    @property
    def supported_features(self):
        """Flag supported features."""
        return 0

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Component added, restore_state using platforms."""
        if hasattr(self, 'async_restore_state'):
            yield from async_restore_state(self, extract_info)
