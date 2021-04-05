"""Module representing a Rako Bridge."""
import asyncio
import logging

from python_rako import Bridge
from python_rako.helpers import convert_to_brightness, get_dg_listener
from python_rako.model import ChannelStatusMessage, SceneStatusMessage, StatusMessage

from .const import DATA_RAKO_LIGHT_MAP, DATA_RAKO_LISTENER_TASK, DOMAIN
from .util import create_unique_id

_LOGGER = logging.getLogger(__name__)


def _state_update(bridge, status_message: StatusMessage):
    light_unique_id = create_unique_id(
        bridge.entry_id, status_message.room, status_message.channel
    )
    brightness = 0
    if isinstance(status_message, ChannelStatusMessage):
        brightness = status_message.brightness
    elif isinstance(status_message, SceneStatusMessage):
        for _channel, _brightness in bridge.level_cache.get_channel_levels(
            status_message.room, status_message.scene
        ):
            _msg = ChannelStatusMessage(status_message.room, _channel, _brightness)
            _state_update(bridge, _msg)
        brightness = convert_to_brightness(status_message.scene)

    listening_light = bridge.get_listening_light(light_unique_id)
    if listening_light:
        listening_light.brightness = brightness
    else:
        _LOGGER.debug("Light not listening: %s", status_message)


async def listen_for_state_updates(bridge):
    """Listen for state updates worker method."""
    async with get_dg_listener(bridge.port) as listener:
        while True:
            message = await bridge.next_pushed_message(listener)
            if message and isinstance(message, StatusMessage):
                _state_update(bridge, message)


class RakoBridge(Bridge):
    """Represents a Rako Bridge."""

    def __init__(self, host, port, entry_id, hass):
        """Init subclass of python_rako Bridge."""
        super().__init__(host, port)
        self.entry_id = entry_id
        self.hass = hass

    @property
    def _light_map(self):
        return self.hass.data[DOMAIN][self.entry_id][DATA_RAKO_LIGHT_MAP]

    @property
    def _listener_task(self):
        return self.hass.data[DOMAIN][self.entry_id][DATA_RAKO_LISTENER_TASK]

    @_listener_task.setter
    def _listener_task(self, task):
        self.hass.data[DOMAIN][self.entry_id][DATA_RAKO_LISTENER_TASK] = task

    def get_listening_light(self, light_unique_id):
        """Return the Light, if listening."""
        light_map = self._light_map
        return light_map.get(light_unique_id)

    def _add_listening_light(self, light):
        light_map = self._light_map
        light_map[light.unique_id] = light

    def _remove_listening_light(self, light):
        light_map = self._light_map
        if light.unique_id in light_map:
            del light_map[light.unique_id]

    async def listen_for_state_updates(self):
        """Background task to listen for state updates."""
        self._listener_task = asyncio.create_task(
            listen_for_state_updates(self), name=DATA_RAKO_LISTENER_TASK
        )

    async def stop_listening_for_state_updates(self):
        """Background task to stop listening for state updates."""
        listener_task = self._listener_task
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

    async def register_for_state_updates(self, light):
        """Register a light to listen for state updates."""
        self._add_listening_light(light)
        if len(self._light_map) == 1:
            await self.listen_for_state_updates()

    async def deregister_for_state_updates(self, light):
        """Deregister a light to listen for state updates."""
        self._remove_listening_light(light)
        if not self._light_map:
            await self.stop_listening_for_state_updates()
