"""Support for Climate devices of (EMEA/EU-based) Honeywell TCC systems."""
from datetime import datetime
import logging
from typing import Any, Dict, Optional, List

import requests.exceptions
import evohomeclient2

from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT, HVAC_MODE_AUTO, HVAC_MODE_OFF,
    PRESET_AWAY, PRESET_ECO, PRESET_HOME,
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_PRESET_MODE)
from homeassistant.const import PRECISION_TENTHS
from homeassistant.util.dt import parse_datetime

from . import CONF_LOCATION_IDX, _handle_exception, EvoDevice
from .const import (
    DOMAIN, EVO_RESET, EVO_AUTO, EVO_AUTOECO, EVO_AWAY, EVO_DAYOFF, EVO_CUSTOM,
    EVO_HEATOFF, EVO_FOLLOW, EVO_TEMPOVER, EVO_PERMOVER)

_LOGGER = logging.getLogger(__name__)

PRESET_RESET = 'Reset'  # reset all child zones to EVO_FOLLOW
PRESET_CUSTOM = 'Custom'

HA_HVAC_TO_TCS = {
    HVAC_MODE_OFF: EVO_HEATOFF,
    HVAC_MODE_HEAT: EVO_AUTO,
}

HA_PRESET_TO_TCS = {
    PRESET_AWAY: EVO_AWAY,
    PRESET_CUSTOM: EVO_CUSTOM,
    PRESET_ECO: EVO_AUTOECO,
    PRESET_HOME: EVO_DAYOFF,
    PRESET_RESET: EVO_RESET,
}
TCS_PRESET_TO_HA = {v: k for k, v in HA_PRESET_TO_TCS.items()}

EVO_PRESET_TO_HA = {
    EVO_FOLLOW: None,
    EVO_TEMPOVER: 'temporary',
    EVO_PERMOVER: 'permanent',
}
HA_PRESET_TO_EVO = {v: k for k, v in EVO_PRESET_TO_HA.items()
                    if v is not None}


def setup_platform(hass, hass_config, add_entities,
                   discovery_info=None) -> None:
    """Create the evohome Controller, and its Zones, if any."""
    broker = hass.data[DOMAIN]['broker']
    loc_idx = broker.params[CONF_LOCATION_IDX]

    _LOGGER.debug(
        "Found Location/Controller, id=%s [%s], name=%s (location_idx=%s)",
        broker.tcs.systemId, broker.tcs.modelType, broker.tcs.location.name,
        loc_idx)

    # special case of RoundThermostat (is single zone)
    if broker.config['zones'][0]['modelType'] == 'RoundModulation':
        zone = list(broker.tcs.zones.values())[0]
        _LOGGER.debug(
            "Found %s, id=%s [%s], name=%s",
            zone.zoneType, zone.zoneId, zone.modelType, zone.name)

        add_entities([EvoThermostat(broker, zone)], update_before_add=True)
        return

    controller = EvoController(broker, broker.tcs)

    zones = []
    for zone in broker.tcs.zones.values():
        _LOGGER.debug(
            "Found %s, id=%s [%s], name=%s",
            zone.zoneType, zone.zoneId, zone.modelType, zone.name)
        zones.append(EvoZone(broker, zone))

    add_entities([controller] + zones, update_before_add=True)


class EvoClimateDevice(EvoDevice, ClimateDevice):
    """Base for a Honeywell evohome Climate device."""

    def __init__(self, evo_broker, evo_device) -> None:
        """Initialize the evohome Climate device."""
        super().__init__(evo_broker, evo_device)

        self._preset_modes = None

    def _set_temperature(self, temperature: float,
                         until: Optional[datetime] = None) -> None:
        """Set a new target temperature for the Zone.

        until == None means indefinitely (i.e. PermanentOverride)
        """
        try:
            self._evo_device.set_temperature(temperature, until)
        except (requests.exceptions.RequestException,
                evohomeclient2.AuthenticationError) as err:
            _handle_exception(err)

    def _set_zone_mode(self, op_mode: str) -> None:
        """Set the Zone to one of its native EVO_* operating modes.

        NB: evohome Zones 'inherit' their operating mode from the Controller.

        Usually, Zones are in 'FollowSchedule' mode, where their setpoints are
        a function of their schedule, and the Controller's operating_mode, e.g.
        Economy mode is their scheduled setpoint less (usually) 3C.

        However, Zones can override these setpoints, either for a specified
        period of time, 'TemporaryOverride', after which they will revert back
        to 'FollowSchedule' mode, or indefinitely, 'PermanentOverride'.

        Some of the Controller's operating_mode are 'forced' upon the Zone,
        regardless of its override state, e.g. 'HeatingOff' (Zones to min_temp)
        and 'Away' (Zones to 12C).
        """
        if op_mode == EVO_FOLLOW:
            try:
                self._evo_device.cancel_temp_override()
            except (requests.exceptions.RequestException,
                    evohomeclient2.AuthenticationError) as err:
                _handle_exception(err)
            return

        temperature = self._evo_device.setpointStatus['targetHeatTemperature']
        until = None  # EVO_PERMOVER

        if op_mode == EVO_TEMPOVER:
            self._setpoints = self.get_setpoints()
            if self._setpoints:
                until = parse_datetime(self._setpoints['next']['from'])

        self._set_temperature(temperature, until=until)

    def _set_tcs_mode(self, op_mode: str) -> None:
        """Set the Controller to any of its native EVO_* operating modes."""
        try:
            self._evo_tcs._set_status(op_mode)  # noqa: E501; pylint: disable=protected-access
        except (requests.exceptions.RequestException,
                evohomeclient2.AuthenticationError) as err:
            _handle_exception(err)

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes."""
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT]

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes."""
        return self._preset_modes


class EvoZone(EvoClimateDevice):
    """Base for a Honeywell evohome Zone."""

    def __init__(self, evo_broker, evo_device) -> None:
        """Initialize the evohome Zone."""
        super().__init__(evo_broker, evo_device)

        self._name = evo_device.name
        self._icon = 'mdi:radiator'

        self._precision = \
            self._evo_device.setpointCapabilities['valueResolution']
        self._state_attributes = [
            'zoneId', 'activeFaults', 'setpointStatus', 'temperatureStatus',
            'setpoints']

        self._supported_features = SUPPORT_PRESET_MODE | \
            SUPPORT_TARGET_TEMPERATURE
        self._preset_modes = list(HA_PRESET_TO_EVO)

    @property
    def hvac_mode(self) -> str:
        """Return the current operating mode of the evohome Zone."""
        if self._evo_tcs.systemModeStatus['mode'] in [EVO_AWAY, EVO_HEATOFF]:
            return HVAC_MODE_AUTO
        is_off = self.target_temperature <= self.min_temp
        return HVAC_MODE_OFF if is_off else HVAC_MODE_HEAT

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature of the evohome Zone."""
        return (self._evo_device.temperatureStatus['temperature']
                if self._evo_device.temperatureStatus['isAvailable'] else None)

    @property
    def target_temperature(self) -> float:
        """Return the target temperature of the evohome Zone."""
        if self._evo_tcs.systemModeStatus['mode'] == EVO_HEATOFF:
            return self._evo_device.setpointCapabilities['minHeatSetpoint']
        return self._evo_device.setpointStatus['targetHeatTemperature']

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp."""
        if self._evo_tcs.systemModeStatus['mode'] in [EVO_AWAY, EVO_HEATOFF]:
            return TCS_PRESET_TO_HA.get(self._evo_tcs.systemModeStatus['mode'])
        return EVO_PRESET_TO_HA.get(
            self._evo_device.setpointStatus['setpointMode'], 'follow')

    @property
    def min_temp(self) -> float:
        """Return the minimum target temperature of a evohome Zone.

        The default is 5, but is user-configurable within 5-35 (in Celsius).
        """
        return self._evo_device.setpointCapabilities['minHeatSetpoint']

    @property
    def max_temp(self) -> float:
        """Return the maximum target temperature of a evohome Zone.

        The default is 35, but is user-configurable within 5-35 (in Celsius).
        """
        return self._evo_device.setpointCapabilities['maxHeatSetpoint']

    def set_temperature(self, **kwargs) -> None:
        """Set a new target temperature for an hour."""
        until = kwargs.get('until')
        if until:
            until = parse_datetime(until)

        self._set_temperature(kwargs['temperature'], until)

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set an operating mode for the Zone."""
        if hvac_mode == HVAC_MODE_OFF:
            self._set_temperature(self.min_temp, until=None)

        else:  # HVAC_MODE_HEAT
            self._set_zone_mode(EVO_FOLLOW)

    def set_preset_mode(self, preset_mode: Optional[str]) -> None:
        """Set a new preset mode.

        If preset_mode is None, then revert to following the schedule.
        """
        self._set_zone_mode(HA_PRESET_TO_EVO.get(preset_mode, EVO_FOLLOW))


class EvoController(EvoClimateDevice):
    """Base for a Honeywell evohome Controller (hub).

    The Controller (aka TCS, temperature control system) is the parent of all
    the child (CH/DHW) devices.  It is also a Climate device.
    """

    def __init__(self, evo_broker, evo_device) -> None:
        """Initialize the evohome Controller (hub)."""
        super().__init__(evo_broker, evo_device)

        self._name = evo_device.location.name
        self._icon = 'mdi:thermostat'

        self._precision = PRECISION_TENTHS
        self._state_attributes = [
            'systemId', 'activeFaults', 'systemModeStatus']

        self._supported_features = SUPPORT_PRESET_MODE
        self._preset_modes = list(HA_PRESET_TO_TCS)

    @property
    def hvac_mode(self) -> str:
        """Return the current operating mode of the evohome Controller."""
        tcs_mode = self._evo_device.systemModeStatus['mode']
        return HVAC_MODE_OFF if tcs_mode == EVO_HEATOFF else HVAC_MODE_HEAT

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the average current temperature of the heating Zones.

        Controllers do not have a current temp, but one is expected by HA.
        """
        temps = [z.temperatureStatus['temperature']
                 for z in self._evo_device.zones.values()
                 if z.temperatureStatus['isAvailable']]
        return round(sum(temps) / len(temps), 1) if temps else None

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the average target temperature of the heating Zones.

        Controllers do not have a target temp, but one is expected by HA.
        """
        temps = [z.setpointStatus['targetHeatTemperature']
                 for z in self._evo_device.zones.values()]
        return round(sum(temps) / len(temps), 1) if temps else None

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp."""
        return TCS_PRESET_TO_HA.get(self._evo_device.systemModeStatus['mode'])

    @property
    def min_temp(self) -> float:
        """Return the minimum target temperature  of the heating Zones.

        Controllers do not have a min target temp, but one is required by HA.
        """
        temps = [z.setpointCapabilities['minHeatSetpoint']
                 for z in self._evo_device.zones.values()]
        return min(temps) if temps else 5

    @property
    def max_temp(self) -> float:
        """Return the maximum target temperature  of the heating Zones.

        Controllers do not have a max target temp, but one is required by HA.
        """
        temps = [z.setpointCapabilities['maxHeatSetpoint']
                 for z in self._evo_device.zones.values()]
        return max(temps) if temps else 35

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set an operating mode for the Controller."""
        self._set_tcs_mode(HA_HVAC_TO_TCS.get(hvac_mode))

    def set_preset_mode(self, preset_mode: Optional[str]) -> None:
        """Set a new preset mode.

        If preset_mode is None, then revert to 'Auto' mode.
        """
        self._set_tcs_mode(HA_PRESET_TO_TCS.get(preset_mode, EVO_AUTO))

    def update(self) -> None:
        """Get the latest state data."""
        pass


class EvoThermostat(EvoZone):
    """Base for a Honeywell Round Thermostat.

    Implemented as a combined Controller/Zone.
    """

    def __init__(self, evo_broker, evo_device) -> None:
        """Initialize the Round Thermostat."""
        super().__init__(evo_broker, evo_device)

        self._name = evo_broker.tcs.location.name
        self._icon = 'mdi:radiator'

        self._preset_modes = [PRESET_AWAY, PRESET_ECO]

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """Return the device-specific state attributes."""
        status = super().device_state_attributes['status']

        status['systemModeStatus'] = getattr(self._evo_tcs, 'systemModeStatus')
        status['activeFaults'] += getattr(self._evo_tcs, 'activeFaults')

        return {'status': status}

    @property
    def hvac_mode(self) -> str:
        """Return the current operating mode."""
        if self._evo_tcs.systemModeStatus['mode'] == EVO_HEATOFF:
            return HVAC_MODE_OFF

        return super().hvac_mode

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp."""
        if self._evo_tcs.systemModeStatus['mode'] == EVO_AUTOECO and \
                self._evo_device.setpointStatus['setpointMode'] == EVO_FOLLOW:
            return PRESET_ECO

        return super().preset_mode

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set an operating mode."""
        self._set_tcs_mode(HA_HVAC_TO_TCS.get(hvac_mode))

    def set_preset_mode(self, preset_mode: Optional[str]) -> None:
        """Set a new preset mode.

        If preset_mode is None, then revert to following the schedule.
        """
        if preset_mode in list(HA_PRESET_TO_TCS):
            self._set_tcs_mode(HA_PRESET_TO_TCS.get(preset_mode))
        else:
            self._set_zone_mode(HA_PRESET_TO_EVO.get(preset_mode, EVO_FOLLOW))
