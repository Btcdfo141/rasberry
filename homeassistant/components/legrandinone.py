"""
Support for legrandinone components.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/legrandinone/
"""
import asyncio
from collections import defaultdict
from typing import Any, Dict, cast
import functools as ft
import logging
import async_timeout
import numbers

import voluptuous as vol

from homeassistant.const import (
    ATTR_ENTITY_ID, CONF_COMMAND, CONF_HOST, CONF_PORT,
    EVENT_HOMEASSISTANT_STOP, STATE_UNKNOWN)
from homeassistant.core import CoreState, callback
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import (
    async_dispatcher_send, async_dispatcher_connect)


REQUIREMENTS = ['iobl==0.0.4']

_LOGGER = logging.getLogger(__name__)

ATTR_EVENT = 'event'
ATTR_STATE = 'state'

CONF_DEVICE_DEFAULTS = 'device_defaults'
CONF_DEVICE_ID = 'legrand_id'
CONF_DEVICE_TYPE = 'device_type'
CONF_DEVICE_UNIT = 'device_unit'
CONF_COMM_MEDIA = 'media'
CONF_COMM_MODE = 'comm_mode'
CONF_DEVICES = 'devices'
CONF_AUTOMATIC_ADD = 'automatic_add'
CONF_FIRE_EVENT = 'fire_event'
CONF_MEDIA = 'iobl_media'
CONF_COMM_MODE = 'iobl_comm_mode'
CONF_PACKET_TYPE = 'iobl_pkt_type'
CONF_DIMENSION_VALUES = 'iobl_dim_values'
CONF_IGNORE_DEVICES = 'ignore_devices'
CONF_RECONNECT_INTERVAL = 'reconnect_interval'

DATA_DEVICE_REGISTER = 'iobl_device_register'
DATA_ENTITY_LOOKUP = 'iobl_entity_lookup'
DEFAULT_RECONNECT_INTERVAL = 10
DEFAULT_SIGNAL_REPETITIONS = 1
CONNECTION_TIMEOUT = 10

EVENT_BUTTON_PRESSED = 'button_pressed'
EVENT_KEY_ID = 'legrand_id'
EVENT_KEY_COMMAND = 'bus_command'
EVENT_TYPE_COMMAND = 'what'

DEVICE_TYPE_AUTOMATION = 'automation'
DEVICE_TYPE_LIGHT = 'light'

DOMAIN = 'legrandinone'

SERVICE_SEND_COMMAND = 'send_packet'

SIGNAL_AVAILABILITY = 'iobl_device_available'
SIGNAL_HANDLE_EVENT = 'iobl_handle_event_{}'

TMP_ENTITY = 'tmp.{}'

DEVICE_DEFAULTS_SCHEMA = vol.Schema({
    vol.Optional(CONF_FIRE_EVENT, default=False): cv.boolean,
    vol.Optional(CONF_MEDIA, default='plc'): cv.string,
    vol.Optional(CONF_COMM_MODE, default='unicast'): cv.string,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_PORT): vol.Any(cv.port, cv.string),
        vol.Optional(CONF_HOST): cv.string,
        vol.Optional(CONF_RECONNECT_INTERVAL,
                     default=DEFAULT_RECONNECT_INTERVAL): int,
    }),
}, extra=vol.ALLOW_EXTRA)

SEND_COMMAND_SCHEMA = vol.Schema({
    vol.Required(CONF_DEVICE_ID): cv.string,
    vol.Required(CONF_DEVICE_TYPE): cv.string,
    vol.Required(CONF_DEVICE_UNIT): cv.string,
    vol.Required(CONF_COMM_MEDIA): cv.string,
    vol.Required(CONF_COMM_MODE): cv.string,
    vol.Required(CONF_COMMAND): cv.string,
    vol.Optional(CONF_PACKET_TYPE): cv.string,
    vol.Optional(CONF_DIMENSION_VALUES): [cv.string],
})


def identify_event_type(event):
    """Look at event to determine type of device.

    Async friendly.
    """
    if event.get('type') == EVENT_KEY_COMMAND:
        return EVENT_KEY_COMMAND

    return 'unknown'


async def async_setup(hass, config):
    """Set up the IOBL component."""
    from iobl.protocol import create_iobl_connection
    import serial

    # Allow entities to register themselves by device_id to be looked up when
    # new IOBL events arrive to be handled
    hass.data[DATA_ENTITY_LOOKUP] = {
        EVENT_KEY_COMMAND: defaultdict(list),
    }

    # Allow platform to specify function to register new unknown devices
    hass.data[DATA_DEVICE_REGISTER] = {}
    hass.data[DATA_DEVICE_REGISTER][EVENT_KEY_COMMAND] = {}

    async def async_send_command(call):
        """Send legrandinone command."""
        _LOGGER.debug('LegrandInOne command for %s', str(call.data))

        data = cast(Dict[str, Any], {
            'legrand_id': call.data.get(CONF_DEVICE_ID),
            'who': call.data.get(CONF_DEVICE_TYPE),
            'mode': call.data.get(CONF_COMM_MODE),
            'media': call.data.get(CONF_COMM_MEDIA),
            'unit': call.data.get(CONF_DEVICE_UNIT),
            'what': call.data.get(CONF_COMMAND)
        })

        data['type'] = call.data.get(CONF_PACKET_TYPE)
        if data['type'] is None:
            # Default to bus_command packet if not specified.
            data['type'] = 'bus_command'

        data['values'] = call.data.get(CONF_DIMENSION_VALUES)

        if not (await LegrandInOneCommand.send_command(data)):
            _LOGGER.error('Failed LegrandInOne command for %s', str(call.data))

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_COMMAND, async_send_command,
        schema=SEND_COMMAND_SCHEMA)

    @callback
    def event_callback(event):
        """Handle incoming legrandinone events.

        IOBL events arrive as dictionaries of varying content
        depending on their type. Identify the events and distribute
        accordingly.
        """
        event_type = event.get('type')
        _LOGGER.debug('event of type %s: %s', event_type, event)

        # Don't propagate non entity events (eg: version string, ack response)
        if event_type not in hass.data[DATA_ENTITY_LOOKUP]:
            _LOGGER.debug('unhandled event of type: %s', event_type)
            return

        # Lookup entities who registered this device id as device id or alias
        event_id = event.get('legrand_id', None)

        entity_ids = hass.data[DATA_ENTITY_LOOKUP][event_type][event_id]

        if entity_ids:
            # Propagate event to every entity matching the device id
            for entity in entity_ids:
                _LOGGER.debug('passing event to %s', entity)
                async_dispatcher_send(hass,
                                      SIGNAL_HANDLE_EVENT.format(entity),
                                      event)
        else:
            device_type = event.get('who')

            # If device is not yet known, register with platform (if loaded)
            if event_type in hass.data[DATA_DEVICE_REGISTER]:
                if device_type in hass.data[DATA_DEVICE_REGISTER][event_type]:
                    _LOGGER.debug('device_id not known, adding new device')

                    hass.data[DATA_ENTITY_LOOKUP][event_type][
                        event_id].append(TMP_ENTITY.format(event_id))
                    hass.async_create_task(
                        hass.data[DATA_DEVICE_REGISTER][event_type][device_type](event))

                else:
                    _LOGGER.debug('device_id not known and automatic %s add disabled', device_type)
            else:
                _LOGGER.debug('device_id not known and automatic add disabled')

    # When connecting to tcp host instead of serial port (optional)
    host = config[DOMAIN].get(CONF_HOST)
    # TCP port when host configured, otherwise serial port
    port = config[DOMAIN][CONF_PORT]

    @callback
    def reconnect(exc=None):
        """Schedule reconnect after connection has been unexpectedly lost."""
        # Reset protocol binding before starting reconnect
        LegrandInOneCommand.set_iobl_protocol(None)

        async_dispatcher_send(hass, SIGNAL_AVAILABILITY, False)

        # If HA is not stopping, initiate new connection
        if hass.state != CoreState.stopping:
            _LOGGER.warning('disconnected from Iobl, reconnecting')
            hass.async_create_task(connect())

    async def connect():
        """Set up connection and hook it into HA for reconnect/shutdown."""
        _LOGGER.info('Initiating Iobl connection')

        # IOBL create_iobl_connection decides based on the value of host
        # (string or None) if serial or tcp mode should be used

        # Initiate serial/tcp connection to IOBL gateway
        connection = create_iobl_connection(
            port=port,
            host=host,
            event_callback=event_callback,
            disconnect_callback=reconnect,
            loop=hass.loop,
            ignore=None
        )

        try:
            with async_timeout.timeout(CONNECTION_TIMEOUT,
                                       loop=hass.loop):
                transport, protocol = await connection

        except (serial.serialutil.SerialException, ConnectionRefusedError,
                TimeoutError, OSError, asyncio.TimeoutError) as exc:
            reconnect_interval = config[DOMAIN][CONF_RECONNECT_INTERVAL]
            _LOGGER.exception(
                "Error connecting to iobl, reconnecting in %s",
                reconnect_interval)
            # Connection to IOBL device is lost, make entities unavailable
            async_dispatcher_send(hass, SIGNAL_AVAILABILITY, False)

            hass.loop.call_later(reconnect_interval, reconnect, exc)
            return

        # There is a valid connection to a IOBL device now so
        # mark entities as available
        async_dispatcher_send(hass, SIGNAL_AVAILABILITY, True)

        # Bind protocol to command class to allow entities to send commands
        LegrandInOneCommand.set_iobl_protocol(protocol)

        # handle shutdown of IOBL asyncio transport
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP,
                                   lambda x: transport.close())

        _LOGGER.info('Connected to Iobl')

    hass.async_create_task(connect())
    return True


class LegrandInOneDevice(Entity):
    """Representation of an iobl device.

    Contains the common logic for Iobl entities.
    """

    platform = None
    _state = None
    _available = True
    legrand_id = None
    iobl_mode = None
    iobl_media = None

    def __init__(self, device_id, initial_event=None, name=None,
                 fire_event=False, iobl_media='plc', iobl_comm_mode='unicast'):
        """Initialize the device."""
        self._initial_event = initial_event
        self.legrand_id = device_id
        self.iobl_mode = iobl_comm_mode
        self.iobl_media = iobl_media

        if name:
            self._name = name
        else:
            self._name = device_id

        self._should_fire_event = fire_event

    @callback
    def handle_event_callback(self, event):
        """Handle incoming event for device type."""
        # Call platform specific event handler
        self._handle_event(event)

        # Propagate changes through ha
        self.async_schedule_update_ha_state()

        # Put command onto bus for user to subscribe to
        if self._should_fire_event and identify_event_type(
                event) == EVENT_KEY_COMMAND:
            self.hass.bus.async_fire(EVENT_BUTTON_PRESSED, {
                ATTR_ENTITY_ID: self.entity_id,
                ATTR_STATE: event.get(EVENT_TYPE_COMMAND),
            })
            _LOGGER.debug("Fired bus event for %s: %s",
                          self.entity_id, event.get(EVENT_TYPE_COMMAND))

    def _handle_event(self, event):
        """Platform specific event handler."""
        raise NotImplementedError()

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return a name for the device."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        if self.assumed_state:
            return False
        return self._state

    @property
    def assumed_state(self):
        """Assume device state until first device event sets state."""
        return self._state is None

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @callback
    def _availability_callback(self, availability):
        """Update availability state."""
        self._available = availability
        self.async_schedule_update_ha_state()

    async def async_added_to_hass(self):
        """Register update callback."""
        # Remove temporary bogus entity_id if added
#         tmp_entity = TMP_ENTITY.format(self.legrand_id)
#         if tmp_entity in self.hass.data[DATA_ENTITY_LOOKUP][
#                 EVENT_KEY_SENSOR][self.legrand_id]:
#             self.hass.data[DATA_ENTITY_LOOKUP][
#                 EVENT_KEY_SENSOR][self.legrand_id].remove(tmp_entity)

        # Register id and aliases
        self.hass.data[DATA_ENTITY_LOOKUP][
            EVENT_KEY_COMMAND][self.legrand_id].append(self.legrand_id)

        async_dispatcher_connect(self.hass, SIGNAL_AVAILABILITY,
                                 self._availability_callback)
        async_dispatcher_connect(self.hass,
                                 SIGNAL_HANDLE_EVENT.format(self.legrand_id),
                                 self.handle_event_callback)

        # Process the initial event now that the entity is created
        if self._initial_event:
            self.handle_event_callback(self._initial_event)

class LegrandInOneCommand(LegrandInOneDevice):
    """Singleton class to make IOBL command interface available to entities.

    This class is to be inherited by every Entity class that is actionable
    (switches/lights). It exposes the IOBL command interface for these
    entities.

    The IOBL interface is managed as a class level and set during setup (and
    reset on reconnect).
    """

    _protocol = None

    @classmethod
    def set_iobl_protocol(cls, protocol):
        """Set the IOBL asyncio protocol as a class variable."""
        cls._protocol = protocol

    @classmethod
    def is_connected(cls):
        """Return connection status."""
        return bool(cls._protocol)

    @classmethod
    async def send_command(cls, command_data):
        """Send device command to IOBL."""
        return await cls._protocol.send_packet(command_data)

    async def _async_handle_command(self, command, *args):

        if command == 'turn_on':
            cmd = 'on'
            self._state = True

        elif command == 'turn_off':
            cmd = 'off'
            self._state = False

        elif command == 'dim':
            _LOGGER.debug("handling command: %s to iobl device: %s - Level : %d", command, self.legrand_id, args[0])
            # convert brightness to rflink dim level
            cmd = int(args[0] * 100 / 255)
            self._state = True

        elif command == 'toggle':
            cmd = 'on'
            # if the state is unknown or false, it gets set as true
            # if the state is true, it gets set as false
            self._state = self._state in [None, False]

        # Cover options for IOBL
        elif command == 'close_cover':
            cmd = 'move_down'
            self._state = False

        elif command == 'open_cover':
            cmd = 'move_up'
            self._state = True

        elif command == 'stop_cover':
            cmd = 'move_stop'
            self._state = True

        # Send initial command and queue repetitions.
        # This allows the entity state to be updated quickly and not having to
        # wait for all repetitions to be sent
        await self._async_send_command(cmd)

        # Update state of entity
        await self.async_update_ha_state()

    async def _async_send_command(self, cmd):
        """Send a command for device to iobl gateway."""
        _LOGGER.debug(
            "Sending command: %s to iobl device: %s", cmd, self.legrand_id)

        if not self.is_connected():
            raise HomeAssistantError('Cannot send command, not connected!')

        # Puts command on outgoing buffer and returns straight away.
        # IOBL protocol/transport handles asynchronous writing of buffer
        # to serial/tcp device. Does not wait for command send
        # confirmation.
        data = cast(Dict[str, Any], {
            'legrand_id': self.legrand_id,
            'who': self.iobl_type,
            'mode': self.iobl_mode,
            'media': self.iobl_media,
            'unit': self.iobl_unit,
        })

        if isinstance(cmd, numbers.Integral):
            data['type'] = 'set_dimension'
            data['dimension'] = 'go_to_level_time'
            data['values'] = [str(cmd)]
        else:
            data['type'] = 'bus_command'
            data['what'] = cmd

        self.hass.async_create_task(self._protocol.send_packet(data))


class SwitchableLegrandInOneDevice(LegrandInOneCommand):
    """IOBL entity which can switch on/off (eg: light, switch)."""

    """Representation of an IOBL light."""
    def __init__(self, *args, **kwargs):
        """Initialize device type and unit number."""
        self.iobl_type = 'light'
        self.iobl_unit = '0'
        super().__init__(*args, **kwargs)

    def _handle_event(self, event):

        command = event['what']
        if command in ['on']:
            self._state = True
        elif command in ['off']:
            self._state = False

    def async_turn_on(self, **kwargs):
        """Turn the device on."""
        return self._async_handle_command("turn_on")

    def async_turn_off(self, **kwargs):
        """Turn the device off."""
        return self._async_handle_command("turn_off")
