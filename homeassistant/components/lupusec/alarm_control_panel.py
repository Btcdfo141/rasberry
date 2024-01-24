"""Support for Lupusec System alarm control panels."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)

from . import DOMAIN as LUPUSEC_DOMAIN, LupusecDevice

SCAN_INTERVAL = timedelta(seconds=2)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up an alarm control panel for a Lupusec device."""
    data = hass.data[LUPUSEC_DOMAIN][config_entry.entry_id]

    alarm_devices = [LupusecAlarm(data, data.lupusec.get_alarm(), config_entry)]

    async_add_devices(alarm_devices)


class LupusecAlarm(LupusecDevice, AlarmControlPanelEntity):
    """An alarm_control_panel implementation for Lupusec."""

    _attr_icon = "mdi:security"
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
    )

    @property
    def state(self) -> str | None:
        """Return the state of the device."""
        if self._device.is_standby:
            state = STATE_ALARM_DISARMED
        elif self._device.is_away:
            state = STATE_ALARM_ARMED_AWAY
        elif self._device.is_home:
            state = STATE_ALARM_ARMED_HOME
        elif self._device.is_alarm_triggered:
            state = STATE_ALARM_TRIGGERED
        else:
            state = None
        return state

    def alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        self._device.set_away()

    def alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        self._device.set_standby()

    def alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        self._device.set_home()
