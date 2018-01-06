"""
Support for MAX! thermostats using the maxcul component.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/climate.maxcul/
"""
import logging

from homeassistant.components.climate import (
    ClimateDevice, SUPPORT_TARGET_TEMPERATURE, SUPPORT_OPERATION_MODE
)
from homeassistant.const import (
    TEMP_CELSIUS, ATTR_TEMPERATURE
)

from homeassistant.components.maxcul import (
    DATA_MAXCUL, EVENT_THERMOSTAT_UPDATE
)

_LOGGER = logging.getLogger(__name__)

DEPENDS = ['maxcul']

DEFAULT_TEMPERATURE = 12

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Add a new MAX! thermostat."""
    from maxcul import ATTR_DEVICE_ID
    thermostat_id = discovery_info.get(ATTR_DEVICE_ID, None)
    if thermostat_id is None:
        return

    device = MaxCulClimate(hass, thermostat_id)
    add_devices([device])


class MaxCulClimate(ClimateDevice):
    """A MAX! thermostat backed by a CUL stick."""

    def __init__(self, hass, thermostat_id):
        """Initialize a new device for the given thermostat id."""
        from maxcul import (
            ATTR_DEVICE_ID, ATTR_DESIRED_TEMPERATURE,
            ATTR_MEASURED_TEMPERATURE, ATTR_MODE,
            ATTR_BATTERY_LOW
        )
        self.entity_id = "climate.maxcul_thermostat_{:x}".format(thermostat_id)
        self._name = "Thermostat {:x}".format(thermostat_id)
        self._thermostat_id = thermostat_id
        self._maxcul_handle = hass.data[DATA_MAXCUL]
        self._current_temperature = None
        self._target_temperature = None
        self._mode = None
        self._battery_low = None

        def update(event):
            """Callback handler for thermostat update events."""
            thermostat_id = event.data.get(ATTR_DEVICE_ID)
            if thermostat_id != self._thermostat_id:
                return

            current_temperature = event.data.get(ATTR_MEASURED_TEMPERATURE)
            target_temperature = event.data.get(ATTR_DESIRED_TEMPERATURE)
            mode = event.data.get(ATTR_MODE)
            battery_low = event.data.get(ATTR_BATTERY_LOW)

            if current_temperature is not None:
                self._current_temperature = current_temperature
            if target_temperature is not None:
                self._target_temperature = target_temperature
            if mode is not None:
                self._mode = mode
            if battery_low is not None:
                self._battery_low = battery_low

            self.async_schedule_update_ha_state()

        hass.bus.listen(EVENT_THERMOSTAT_UPDATE, update)

        self._maxcul_handle.wakeup(self._thermostat_id)

    @property
    def supported_features(self):
        """Return the features supported by this device."""
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE

    @property
    def should_poll(self):
        """Return whether this device must be polled."""
        return False

    @property
    def name(self):
        """Return the name of this device."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return device specific attributes."""
        from maxcul import ATTR_BATTERY_LOW
        return {
            ATTR_BATTERY_LOW: self._battery_low
        }

    @property
    def max_temp(self):
        """Return the maximum temperature for this device."""
        from maxcul import MAX_TEMPERATURE
        return MAX_TEMPERATURE

    @property
    def min_temp(self):
        """Return the minimum temperature for this device."""
        from maxcul import MIN_TEMPERATURE
        return MIN_TEMPERATURE

    @property
    def temperature_unit(self):
        """Return the temperature unit of this device."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the currently measured temperature of this device."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the target temperature of this device."""
        return self._target_temperature

    @property
    def current_operation(self):
        """Return the current operation mode of this device."""
        return self._mode

    @property
    def operation_list(self):
        """All supported operation modes of this device."""
        from maxcul import MODE_AUTO, MODE_MANUAL, MODE_TEMPORARY, MODE_BOOST
        return [MODE_AUTO, MODE_MANUAL, MODE_TEMPORARY, MODE_BOOST]

    def set_temperature(self, **kwargs):
        """Set the target temperature of this device."""
        from maxcul import MODE_MANUAL
        target_temperature = kwargs.get(ATTR_TEMPERATURE)
        if target_temperature is None:
            return False

        return self._maxcul_handle.set_temperature(
            self._thermostat_id,
            target_temperature,
            self._mode or MODE_MANUAL)

    def set_operation_mode(self, operation_mode):
        """Set the operation mode of this device."""
        return self._maxcul_handle.set_temperature(
            self._thermostat_id,
            self._target_temperature or DEFAULT_TEMPERATURE,
            operation_mode)
