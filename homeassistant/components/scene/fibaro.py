"""
Support for Fibaro scenes.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/scene.fibaro/
"""
import logging

from homeassistant.components.scene import (
    DOMAIN, Scene)
from homeassistant.components.fibaro import (
    FIBARO_CONTROLLER, FIBARO_DEVICES, FibaroDevice)

ENTITY_ID_FORMAT = DOMAIN + '.{}'

DEPENDENCIES = ['fibaro']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Perform the setup for Fibaro scenes."""
    if discovery_info is None:
        return

    add_entities(
        [FibaroScene(scene, hass.data[FIBARO_CONTROLLER])
         for scene in hass.data[FIBARO_DEVICES]['scene']], True)


class FibaroScene(FibaroDevice, Scene):
    """Representation of a Fibaro scene entity."""

    def __init__(self, fibaro_device, controller):
        """Initialize the scene."""
        super().__init__(fibaro_device, controller)
        self.entity_id = ENTITY_ID_FORMAT.format(self.ha_id)

    def update(self):
        """Update the scene status."""
#        self.fibaro_device.refresh()
        pass

    async def async_activate(self):
        """Activate the scene."""
        await self.fibaro_device.start()

    @property
    def name(self):
        """Return the name of the scene."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes of the scene."""
#        return {'fibaro_scene_id': self.fibaro_device..vera_scene_id}
        return self.fibaro_device.properties
