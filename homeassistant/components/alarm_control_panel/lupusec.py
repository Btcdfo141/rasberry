"""
This component provides HA alarm_control_panel support for Lupusec System.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/alarm_control_panel.lupusec/
"""

from datetime import timedelta

from homeassistant.components.alarm_control_panel import AlarmControlPanel
from homeassistant.components.lupusec import LupusecDevice

import homeassistant.util.dt as dt_util

from homeassistant.const import (STATE_ALARM_ARMED_AWAY,
                                 STATE_ALARM_ARMED_HOME,
                                 STATE_ALARM_DISARMED)

DEPENDENCIES = ['lupusec']
DOMAIN = 'lupusec'
ICON = 'mdi:security'

SCAN_INTERVAL = timedelta(seconds=2)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up an alarm control panel for a Lupusec device."""
    data = hass.data[DOMAIN]

    alarm_devices = [LupusecAlarm(data, data.lupusec.get_alarm(), data.name)]

    data.devices.extend(alarm_devices)

    add_entities(alarm_devices)


class LupusecAlarm(LupusecDevice, AlarmControlPanel):
    """An alarm_control_panel implementation for Lupusec."""

    def __init__(self, data, device, name):
        """Initialize the alarm control panel."""
        super().__init__(data, device)
        self._name = name
        self._state = STATE_ALARM_DISARMED
        self._previous_state = ''
        self._state_ts = ''

    @property
    def icon(self):
        """Return the icon."""
        return ICON

    @property
    def state(self):
        """Return the state of the device."""
        if self._device.is_standby:
            state = STATE_ALARM_DISARMED
        elif self._device.is_away:
            state = STATE_ALARM_ARMED_AWAY
        elif self._device.is_home:
            state = STATE_ALARM_ARMED_HOME
        else:
            state = None
        return state

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        self._device.set_away()
        self._update_state(STATE_ALARM_ARMED_AWAY)

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        self._device.set_standby()
        self._update_state(STATE_ALARM_DISARMED)

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        self._device.set_home()
        self._update_state(STATE_ALARM_ARMED_HOME)

    def _update_state(self, state):
        """Update the state."""
        if self._state == state:
            return
        self._previous_state = self._state
        self._state = state
        self._state_ts = dt_util.utcnow()
        self.schedule_update_ha_state()

        # self.async_update_ha_state
