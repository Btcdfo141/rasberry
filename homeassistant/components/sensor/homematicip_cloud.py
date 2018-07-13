"""
Support for HomematicIP sensors.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/sensor.homematicip_cloud/
"""

import logging

from homeassistant.components.homematicip_cloud import (
    HomematicipGenericDevice, DOMAIN as HMIPC_DOMAIN,
    HMIPC_HAPID)
from homeassistant.const import (
    TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE, DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE)

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['homematicip_cloud']

ATTR_VALVE_STATE = 'valve_state'
ATTR_VALVE_POSITION = 'valve_position'
ATTR_TEMPERATURE = 'temperature'
ATTR_TEMPERATURE_OFFSET = 'temperature_offset'
ATTR_HUMIDITY = 'humidity'


async def async_setup_platform(hass, config, async_add_devices,
                               discovery_info=None):
    """Set up the HomematicIP sensors devices."""
    pass


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the HomematicIP sensors from a config entry."""
    from homematicip.device import (
        HeatingThermostat, TemperatureHumiditySensorWithoutDisplay,
        TemperatureHumiditySensorDisplay, MotionDetectorIndoor)

    home = hass.data[HMIPC_DOMAIN][config_entry.data[HMIPC_HAPID]].home
    devices = [HomematicipAccesspointStatus(home)]
    for device in home.devices:
        if isinstance(device, HeatingThermostat):
            devices.append(HomematicipHeatingThermostat(home, device))
        if isinstance(device, (TemperatureHumiditySensorDisplay,
                               TemperatureHumiditySensorWithoutDisplay)):
            devices.append(HomematicipTemperatureSensor(home, device))
            devices.append(HomematicipHumiditySensor(home, device))
        if isinstance(device, MotionDetectorIndoor):
            devices.append(HomematicipIlluminanceSensor(home, device))

    if devices:
        async_add_devices(devices)


class HomematicipAccesspointStatus(HomematicipGenericDevice):
    """Representation of an HomeMaticIP access point."""

    def __init__(self, home):
        """Initialize access point device."""
        super().__init__(home, home)

    @property
    def icon(self):
        """Return the icon of the access point device."""
        return 'mdi:access-point-network'

    @property
    def state(self):
        """Return the state of the access point."""
        return self._home.dutyCycle

    @property
    def available(self):
        """Device available."""
        return self._home.connected

    @property
    def device_state_attributes(self):
        """Return the state attributes of the access point."""
        return {}


class HomematicipHeatingThermostat(HomematicipGenericDevice):
    """MomematicIP heating thermostat representation."""

    def __init__(self, home, device):
        """Initialize heating thermostat device."""
        super().__init__(home, device, 'Heating')

    @property
    def icon(self):
        """Return the icon."""
        from homematicip.base.enums import ValveState

        if self._device.valveState != ValveState.ADAPTION_DONE:
            return 'mdi:alert'
        return 'mdi:radiator'

    @property
    def state(self):
        """Return the state of the radiator valve."""
        from homematicip.base.enums import ValveState

        if self._device.valveState != ValveState.ADAPTION_DONE:
            return self._device.valveState
        return round(self._device.valvePosition*100)

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return '%'


class HomematicipHumiditySensor(HomematicipGenericDevice):
    """MomematicIP humidity device."""

    def __init__(self, home, device):
        """Initialize the thermometer device."""
        super().__init__(home, device, 'Humidity')

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return DEVICE_CLASS_HUMIDITY

    @property
    def icon(self):
        """Return the icon."""
        return 'mdi:water-percent'

    @property
    def state(self):
        """Return the state."""
        return self._device.humidity

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return '%'


class HomematicipTemperatureSensor(HomematicipGenericDevice):
    """MomematicIP the thermometer device."""

    def __init__(self, home, device):
        """Initialize the thermometer device."""
        super().__init__(home, device, 'Temperature')

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return DEVICE_CLASS_TEMPERATURE

    @property
    def icon(self):
        """Return the icon."""
        return 'mdi:thermometer'

    @property
    def state(self):
        """Return the state."""
        return self._device.actualTemperature

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return TEMP_CELSIUS


class HomematicipIlluminanceSensor(HomematicipGenericDevice):
    """MomematicIP the thermometer device."""

    def __init__(self, home, device):
        """Initialize the  device."""
        super().__init__(home, device, 'Illuminance')

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return DEVICE_CLASS_ILLUMINANCE

    @property
    def state(self):
        """Return the state."""
        return self._device.illumination

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return 'lx'
