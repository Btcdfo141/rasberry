"""
Support for Rflink switches.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.rflink/
"""
import asyncio
import logging


from homeassistant.components.rflink import (
    CONF_ALIASSES, CONF_DEVICE_DEFAULTS, CONF_DEVICES, CONF_FIRE_EVENT,
    CONF_GROUP, CONF_GROUP_ALIASSES,  CONF_NOGROUP_ALIASSES,
    CONF_SIGNAL_REPETITIONS, DATA_ENTITY_GROUP_LOOKUP, DATA_ENTITY_LOOKUP,
    DEVICE_DEFAULTS_SCHEMA, DOMAIN, EVENT_KEY_COMMAND, CoverableRflinkDevice,
    cv, vol)
from homeassistant.components.cover import (
    CoverDevice, ATTR_TILT_POSITION, SUPPORT_OPEN_TILT,
    SUPPORT_CLOSE_TILT, SUPPORT_STOP_TILT, SUPPORT_SET_TILT_POSITION,
    SUPPORT_OPEN, SUPPORT_CLOSE, SUPPORT_STOP, SUPPORT_SET_POSITION,
    ATTR_POSITION)
from homeassistant.components.cover import CoverDevice
from homeassistant.const import CONF_NAME, CONF_PLATFORM
DEPENDENCIES = ['rflink']

_LOGGER = logging.getLogger(__name__)


CONF_ALIASES = 'aliases'
CONF_ALIASSES = 'aliases'
CONF_GROUP_ALIASES = 'group_aliases'
CONF_GROUP_ALIASSES = 'group_aliases'
CONF_GROUP = 'group'
CONF_NOGROUP_ALIASES = 'nogroup_aliases'
CONF_NOGROUP_ALIASSES = 'nogroup_aliases'
CONF_DEVICE_DEFAULTS = 'device_defaults'
CONF_DEVICES = 'devices'
CONF_AUTOMATIC_ADD = 'automatic_add'
CONF_FIRE_EVENT = 'fire_event'
CONF_IGNORE_DEVICES = 'ignore_devices'
CONF_RECONNECT_INTERVAL = 'reconnect_interval'
CONF_SIGNAL_REPETITIONS = 'signal_repetitions'
CONF_WAIT_FOR_ACK = 'wait_for_ack'



PLATFORM_SCHEMA = vol.Schema({
    vol.Required(CONF_PLATFORM): DOMAIN,
    vol.Optional(CONF_DEVICE_DEFAULTS, default=DEVICE_DEFAULTS_SCHEMA({})):
    DEVICE_DEFAULTS_SCHEMA,
    vol.Optional(CONF_DEVICES, default={}): vol.Schema({
        cv.string: {
            vol.Optional(CONF_NAME): cv.string,
            vol.Optional(CONF_ALIASSES, default=[]):
                vol.All(cv.ensure_list, [cv.string]),
            vol.Optional(CONF_GROUP_ALIASSES, default=[]):
                vol.All(cv.ensure_list, [cv.string]),
            vol.Optional(CONF_NOGROUP_ALIASSES, default=[]):
                vol.All(cv.ensure_list, [cv.string]),
            vol.Optional(CONF_FIRE_EVENT, default=False): cv.boolean,
            vol.Optional(CONF_SIGNAL_REPETITIONS): vol.Coerce(int),
            vol.Optional(CONF_GROUP, default=True): cv.boolean,
        },
    }),
})


def devices_from_config(domain_config, hass=None):
    """Parse configuration and add Rflink switch devices."""
    devices = []
    for device_id, config in domain_config[CONF_DEVICES].items():
        device_config = dict(domain_config[CONF_DEVICE_DEFAULTS], **config)
        device = RflinkCover(device_id, hass, **device_config)
        devices.append(device)

        # Register entity (and aliasses) to listen to incoming rflink events
        # Device id and normal aliasses respond to normal and group command
        hass.data[DATA_ENTITY_LOOKUP][
            EVENT_KEY_COMMAND][device_id].append(device)
        if config[CONF_GROUP]:
            hass.data[DATA_ENTITY_GROUP_LOOKUP][
                EVENT_KEY_COMMAND][device_id].append(device)
        for _id in config[CONF_ALIASSES]:
            hass.data[DATA_ENTITY_LOOKUP][
                EVENT_KEY_COMMAND][_id].append(device)
            hass.data[DATA_ENTITY_GROUP_LOOKUP][
                EVENT_KEY_COMMAND][_id].append(device)
        # group_aliasses only respond to group commands
        #for _id in config[CONF_GROUP_ALIASSES]:
        #    hass.data[DATA_ENTITY_GROUP_LOOKUP][
        #        EVENT_KEY_COMMAND][_id].append(device)
        # nogroup_aliasses only respond to normal commands
        #for _id in config[CONF_NOGROUP_ALIASSES]:
        #    hass.data[DATA_ENTITY_LOOKUP][
        #        EVENT_KEY_COMMAND][_id].append(device)

    return devices


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Rflink platform."""
    async_add_devices(devices_from_config(config, hass))


class RflinkCover(CoverableRflinkDevice, CoverDevice):
    """Representation of a Rflink cover."""

    pass