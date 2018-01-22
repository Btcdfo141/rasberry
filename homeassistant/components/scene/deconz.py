"""
Support for deCONZ scenes.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/scene.deconz/
"""
import asyncio

from homeassistant.components.deconz import (
    DOMAIN as DECONZ_DATA, DECONZ_ENTITIES)
from homeassistant.components.scene import Scene

DEPENDENCIES = ['deconz']


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up scenes for deCONZ component."""
    if discovery_info is None:
        return

    scenes = hass.data[DECONZ_DATA].scenes
    entities = []

    for scene in scenes.values():
        entities.append(DeconzScene(scene))
    async_add_devices(entities)
    hass.data[DECONZ_ENTITIES] = hass.data[DECONZ_ENTITIES] + entities


class DeconzScene(Scene):
    """Representation of a deCONZ scene."""

    def __init__(self, scene):
        """Set up a scene."""
        self._scene = scene

    @asyncio.coroutine
    def async_activate(self):
        """Activate the scene."""
        yield from self._scene.async_set_state({})

    @property
    def name(self):
        """Return the name of the scene."""
        return self._scene.full_name

    @property
    def deconz_id(self):
        """Return the deconz id of the scene.

        E.g. /groups/1/scenes/1.
        """
        return self._scene._deconz_id
