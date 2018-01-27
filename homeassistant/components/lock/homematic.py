"""
Support for Homematic lock.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/lock.homematic/
"""
import logging
from homeassistant.components.lock import LockDevice
from homeassistant.components.homematic import HMDevice, ATTR_DISCOVER_DEVICES
from homeassistant.const import STATE_UNKNOWN


_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['homematic']


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Homematic lock platform."""
    if discovery_info is None:
        return

    devices = []
    for conf in discovery_info[ATTR_DISCOVER_DEVICES]:
        new_device = HMLock(conf)
        devices.append(new_device)

    add_devices(devices)


class HMLock(HMDevice, LockDevice):
    """Representation of a Homematic lock aka KeyMatic."""

    @property
    def is_locked(self):
        """Return true if the lock is locked."""
        return self._hmdevice.is_locked()

    def lock(self, **kwargs):
        """Lock the lock."""
        self._hmdevice.lock()

    def unlock(self, **kwargs):
        """Unlock the lock."""
        self._hmdevice.unlock()

    def open(self, **kwargs):
        """Opens the door lock."""
        self._hmdevice.open()

    def _init_data_struct(self):
        """Generate the data dictionary (self._data) from metadata."""
        self._state = "STATE"
        self._data.update({self._state: STATE_UNKNOWN})