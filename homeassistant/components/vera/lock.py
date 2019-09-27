"""Support for Vera locks."""
import logging

from homeassistant.components.lock import ENTITY_ID_FORMAT, LockDevice
from homeassistant.const import STATE_LOCKED, STATE_UNLOCKED

from . import VERA_CONTROLLER, VERA_DEVICES, VeraDevice

_LOGGER = logging.getLogger(__name__)

ATTR_LAST_USER_ID = "last_user_id"
ATTR_LAST_USER_NAME = "last_user_name"
ATTR_LOW_BATTERY = "low_battery"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Find and return Vera locks."""
    add_entities(
        [
            VeraLock(device, hass.data[VERA_CONTROLLER])
            for device in hass.data[VERA_DEVICES]["lock"]
        ],
        True,
    )


class VeraLock(VeraDevice, LockDevice):
    """Representation of a Vera lock."""

    def __init__(self, vera_device, controller):
        """Initialize the Vera device."""
        self._state = None
        VeraDevice.__init__(self, vera_device, controller)
        self.entity_id = ENTITY_ID_FORMAT.format(self.vera_id)

    def lock(self, **kwargs):
        """Lock the device."""
        self.vera_device.lock()
        self._state = STATE_LOCKED

    def unlock(self, **kwargs):
        """Unlock the device."""
        self.vera_device.unlock()
        self._state = STATE_UNLOCKED

    @property
    def is_locked(self):
        """Return true if device is on."""
        return self._state == STATE_LOCKED

    @property
    def device_state_attributes(self):
        """Return the state attributes of the lock."""
        data = super().device_state_attributes

        # FIXME: this check will no longer be required once the version of the
        # pyvera library with these two functions included is generally
        # available.
        if ("get_last_user_alert" in dir(self.vera_device)) and (
            "get_low_battery_alert" in dir(self.vera_device)
        ):
            last_user = self.vera_device.get_last_user_alert()
            if last_user is not None:
                data[ATTR_LAST_USER_ID] = last_user[0]
                data[ATTR_LAST_USER_NAME] = last_user[1]
            else:
                data[ATTR_LAST_USER_ID] = -1
                data[ATTR_LAST_USER_NAME] = ""

            data[ATTR_LOW_BATTERY] = self.vera_device.get_low_battery_alert()

        return data

    def update(self):
        """Update state by the Vera device callback."""
        self._state = (
            STATE_LOCKED if self.vera_device.is_locked(True) else STATE_UNLOCKED
        )
