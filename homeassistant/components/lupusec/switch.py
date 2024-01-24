"""Support for Lupusec Security System switches."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

import lupupy.constants as CONST

from homeassistant.components.switch import SwitchEntity

from . import DOMAIN, LupusecDevice

SCAN_INTERVAL = timedelta(seconds=2)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up Lupusec switch devices."""

    data = hass.data[DOMAIN][config_entry.entry_id]

    device_types = CONST.TYPE_SWITCH

    switches = []
    for device in data.lupusec.get_devices(generic_type=device_types):
        switches.append(LupusecSwitch(data, device, config_entry))

    async_add_devices(switches)


class LupusecSwitch(LupusecDevice, SwitchEntity):
    """Representation of a Lupusec switch."""

    def turn_on(self, **kwargs: Any) -> None:
        """Turn on the device."""
        self._device.switch_on()

    def turn_off(self, **kwargs: Any) -> None:
        """Turn off the device."""
        self._device.switch_off()

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._device.is_on
