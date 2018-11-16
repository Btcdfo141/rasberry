"""
Connects to Teletask platform.

"""

import logging

import voluptuous as vol

from homeassistant.const import (CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers import discovery
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_state_change
# from homeassistant.helpers.script import Script

REQUIREMENTS = ['teletask==0.0.1']

DOMAIN = "teletask"

ATTR_DISCOVER_DEVICES = 'devices'

_LOGGER = logging.getLogger(__name__)

CONF_TELETASK_CONFIG = ''
CONF_TELETASK_FIRE_EVENT = "fire_event"
DATA_TELETASK = 'data_teletask'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.port,
         vol.Inclusive(CONF_TELETASK_FIRE_EVENT, 'fire_ev'):
            cv.boolean
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Set up the TELETASK component."""
    from teletask.exceptions import TeletaskException
    try:
        hass.data[DATA_TELETASK] = TeletaskModule(hass, config)
        await hass.data[DATA_TELETASK].start()

    except TeletaskException as ex:
        _LOGGER.warning("Can't connect to TELETASK interface: %s", ex)
        hass.components.persistent_notification.async_create(
            "Can't connect to TELETASK interface: <br>"
            "<b>{0}</b>".format(ex),
            title="TELETASK")

    hass.services.async_register(
        DOMAIN, "SERVICE_TELETASK_SEND",
        hass.data[DATA_TELETASK].service_send_to_teletask_bus)

    return True


def _get_devices(hass, discovery_type):
    """Get the TELETASK devices."""
    return list(
        map(lambda device: device.name,
            filter(
                lambda device: type(device).__name__ == discovery_type,
                hass.data[DATA_TELETASK].teletask.devices)))


class TeletaskModule:
    """Representation of TELETASK Object."""

    def __init__(self, hass, config):
        """Initialize of TELETASK module."""
        self.hass = hass
        self.config = config
        self.connected = False
        self.init_teletask()
        self.register_callbacks()
        self.exposures = []

    def init_teletask(self):
        """Initialize of TELETASK object."""
        from teletask import Teletask
        self.teletask = Teletask(config=None, loop=self.hass.loop)

    async def start(self):
        """Start TELETASK object. Connect to tunneling or Routing device."""
        await self.teletask.start(host="192.168.97.31", port=55957)
        await self.teletask.register_feedback()

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.stop)
        self.connected = True

    async def stop(self, event):
        """Stop TELETASK object. Disconnect from tunneling or Routing device."""
        await self.teletask.stop()

    def register_callbacks(self):
        """Register callbacks within teletask object."""
        if CONF_TELETASK_FIRE_EVENT in self.config[DOMAIN] and \
                self.config[DOMAIN][CONF_TELETASK_FIRE_EVENT]:
            print("HASS: Callback  102")
            self.teletask.telegram_queue.register_telegram_received_cb(self.telegram_received_cb)

    async def telegram_received_cb(self, telegram):
        print("REC", telegram)
        """Call invoked after a TELETASK telegram was received."""
        self.hass.bus.async_fire('teletask_event', {
            'address': str(telegram.group_address),
            'data': telegram.payload.value
        })
        # False signals teletask to proceed with processing telegrams.
        return False

    async def service_send_to_teletask_bus(self, call):
        """Service for sending an arbitrary TELETASK message to the TELETASK bus."""
        from teletask.teletask import Telegram, GroupAddress, DPTBinary, DPTArray
        attr_payload = call.data.get(SERVICE_TELETASK_ATTR_PAYLOAD)
        attr_address = call.data.get(SERVICE_TELETASK_ATTR_ADDRESS)

        def calculate_payload(attr_payload):
            """Calculate payload depending on type of attribute."""
            if isinstance(attr_payload, int):
                return DPTBinary(attr_payload)
            return DPTArray(attr_payload)
        payload = calculate_payload(attr_payload)
        address = GroupAddress(attr_address)

        telegram = Telegram()
        telegram.payload = payload
        telegram.group_address = address
        await self.teletask.telegrams.put(telegram)


# class TELETASKAutomation():
#     """Wrapper around teletask.devices.ActionCallback object.."""

#     def __init__(self, hass, device, hook, action, counter=1):
#         """Initialize Automation class."""
#         self.hass = hass
#         self.device = device
#         script_name = "{} turn ON script".format(device.get_name())
#         self.script = Script(hass, action, script_name)

#         import teletask
#         self.action = teletask.devices.ActionCallback(
#             hass.data[DATA_TELETASK].teletask, self.script.async_run,
#             hook=hook, counter=counter)
#         device.actions.append(self.action)