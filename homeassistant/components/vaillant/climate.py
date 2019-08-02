"""Interfaces with Vaillant climate."""

import abc
import logging
from typing import Optional, List, Dict

from vr900connector.model import System, Room, Component, QuickMode, Zone, \
    HeatingMode, Mode

from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import \
    SUPPORT_TARGET_TEMPERATURE, DOMAIN, SUPPORT_TARGET_TEMPERATURE_RANGE, \
    ATTR_TARGET_TEMP_LOW, ATTR_TARGET_TEMP_HIGH, SUPPORT_PRESET_MODE, \
    HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_AUTO, PRESET_AWAY, \
    HVAC_MODE_FAN_ONLY, PRESET_COMFORT, PRESET_BOOST, \
    PRESET_SLEEP, PRESET_HOME, HVAC_MODE_COOL
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE

from . import HUB, BaseVaillantEntity, CONF_ROOM_CLIMATE, CONF_ZONE_CLIMATE


_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the Vaillant climate platform."""
    climates = []
    hub = hass.data[HUB]

    if hub.system:
        if hub.config[CONF_ZONE_CLIMATE]:
            for zone in hub.system.zones:
                if not zone.rbr:
                    entity = VaillantZoneClimate(hub.system, zone)
                    hub.add_listener(entity)
                    climates.append(entity)

        if hub.config[CONF_ROOM_CLIMATE]:
            for room in hub.system.rooms:
                entity = VaillantRoomClimate(hub.system, room)
                hub.add_listener(entity)
                climates.append(entity)

    _LOGGER.info("Adding %s climate entities", len(climates))

    async_add_entities(climates)
    return True


class VaillantClimate(BaseVaillantEntity, ClimateDevice, abc.ABC):
    """Base class for climate."""

    def __init__(self, system: System, comp_name, comp_id,
                 component: Component):
        """Initialize entity."""
        super().__init__(DOMAIN, None, comp_name, comp_id)
        self._system = None
        self._component = None
        self._active_mode = None
        self._refresh(system, component)

    @property
    def available(self):
        """Return True if entity is available."""
        return self._component is not None

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        _LOGGER.debug("Target temp is %s",
                      self._active_mode.target_temperature)
        return self._active_mode.target_temperature

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._component.current_temperature

    @property
    def is_aux_heat(self) -> Optional[bool]:
        """Return true if aux heater."""
        return False

    @property
    def fan_mode(self) -> Optional[str]:
        """Return the fan setting."""
        return None

    @property
    def fan_modes(self) -> Optional[List[str]]:
        """Return the list of available fan modes."""
        return None

    @property
    def swing_mode(self) -> Optional[str]:
        """Return the swing setting."""
        return None

    @property
    def swing_modes(self) -> Optional[List[str]]:
        """Return the list of available swing modes."""
        return None

    def set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        pass

    def set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        pass

    def set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        pass

    def turn_aux_heat_on(self) -> None:
        """Turn auxiliary heater on."""
        pass

    def turn_aux_heat_off(self) -> None:
        """Turn auxiliary heater off."""
        pass

    async def vaillant_update(self):
        """Update specific for vaillant."""
        self._refresh(self.hub.system,
                      self.hub.find_component(self._component))

    def _refresh(self, system, component):
        """Refresh the entity."""
        self._system = system
        self._component = component
        self._active_mode = self.get_active_mode()

    @abc.abstractmethod
    def get_active_mode(self):
        """Get active mode of the climate."""
        pass


class VaillantRoomClimate(VaillantClimate):
    """Climate for a room."""

    _MODE_TO_PRESET = {
        HeatingMode.QUICK_VETO: PRESET_BOOST,
        HeatingMode.AUTO: PRESET_COMFORT,
        HeatingMode.ON: PRESET_HOME,
        HeatingMode.OFF: PRESET_SLEEP,
        HeatingMode.MANUAL: PRESET_COMFORT,
        QuickMode.QM_HOLIDAY: PRESET_AWAY,
        QuickMode.QM_SYSTEM_OFF: PRESET_SLEEP
    }

    _MODE_TO_HVAC: Dict[Mode, str] = {
        HeatingMode.QUICK_VETO: HVAC_MODE_HEAT,
        HeatingMode.ON: HVAC_MODE_HEAT,
        HeatingMode.MANUAL: HVAC_MODE_HEAT,

        HeatingMode.AUTO: HVAC_MODE_AUTO,

        HeatingMode.OFF: HVAC_MODE_OFF,
        QuickMode.QM_HOLIDAY: HVAC_MODE_OFF,
        QuickMode.QM_SYSTEM_OFF: HVAC_MODE_OFF
    }

    _HVAC_TO_MODE: Dict[str, Mode] = {
        HVAC_MODE_AUTO: HeatingMode.AUTO,
        HVAC_MODE_OFF: HeatingMode.OFF,
        HVAC_MODE_HEAT: HeatingMode.MANUAL
    }

    _SUPPORTED_HVAC_MODE = list(set(_MODE_TO_HVAC.values()))

    _SUPPORTED_PRESET_MODE = list(set(_MODE_TO_PRESET.values()))

    def __init__(self, system: System, room: Room):
        """Initialize entity."""
        super().__init__(system, room.name, room.name, room)
        self._active_mode = system.get_active_mode_room(room)
        self._supported_features = SUPPORT_TARGET_TEMPERATURE \
            | SUPPORT_PRESET_MODE

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        return self._MODE_TO_HVAC[self._active_mode.current_mode]

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes."""
        return self._SUPPORTED_HVAC_MODE

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp."""
        return self._MODE_TO_PRESET[self._active_mode.current_mode]

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes."""
        return self._SUPPORTED_PRESET_MODE

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._supported_features

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return Room.MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return Room.MAX_TEMP

    def get_active_mode(self):
        """Get active mode of the climate."""
        return self._system.get_active_mode_room(self._component)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        self.hub.set_room_target_temperature(
            self, self._component, float(kwargs.get(ATTR_TEMPERATURE)))

    def set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if PRESET_AWAY == preset_mode:
            self.hub.set_room_operation_mode(self, self._component,
                                             HeatingMode.OFF.name)
        else:
            self.hub.set_room_operation_mode(self, self._component,
                                             HeatingMode.AUTO.name)

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        mode = self._HVAC_TO_MODE[hvac_mode]
        self.hub.set_zone_operation_mode(self, self._component, mode)

    @property
    def target_temperature_high(self) -> Optional[float]:
        """Return the highbound target temperature we try to reach."""
        return None

    @property
    def target_temperature_low(self) -> Optional[float]:
        """Return the lowbound target temperature we try to reach."""
        return None


class VaillantZoneClimate(VaillantClimate):
    """Climate for a zone."""

    _MODE_TO_PRESET = {
        HeatingMode.QUICK_VETO: PRESET_BOOST,
        HeatingMode.AUTO: PRESET_COMFORT,
        HeatingMode.NIGHT: PRESET_SLEEP,
        HeatingMode.DAY: PRESET_HOME,
        HeatingMode.OFF: PRESET_SLEEP,
        QuickMode.QM_ONE_DAY_AWAY: PRESET_AWAY,
        QuickMode.QM_HOLIDAY: PRESET_AWAY,
        QuickMode.QM_ONE_DAY_AT_HOME: PRESET_COMFORT,
        QuickMode.QM_PARTY: PRESET_COMFORT,
        QuickMode.QM_SYSTEM_OFF: PRESET_SLEEP,
        QuickMode.QM_VENTILATION_BOOST: PRESET_BOOST
    }

    _MODE_TO_HVAC: Dict[Mode, str] = {
        HeatingMode.QUICK_VETO: HVAC_MODE_HEAT,
        HeatingMode.DAY: HVAC_MODE_HEAT,
        QuickMode.QM_PARTY: HVAC_MODE_HEAT,

        HeatingMode.NIGHT: HVAC_MODE_COOL,

        HeatingMode.AUTO: HVAC_MODE_AUTO,
        QuickMode.QM_ONE_DAY_AT_HOME: HVAC_MODE_AUTO,

        HeatingMode.OFF: HVAC_MODE_OFF,
        QuickMode.QM_ONE_DAY_AWAY: HVAC_MODE_OFF,
        QuickMode.QM_HOLIDAY: HVAC_MODE_OFF,
        QuickMode.QM_SYSTEM_OFF: HVAC_MODE_OFF,

        QuickMode.QM_VENTILATION_BOOST: HVAC_MODE_FAN_ONLY
    }

    _HVAC_TO_MODE: Dict[str, Mode] = {
        HVAC_MODE_COOL: HeatingMode.NIGHT,
        HVAC_MODE_AUTO: HeatingMode.AUTO,
        HVAC_MODE_OFF: HeatingMode.OFF,
        HVAC_MODE_HEAT: HeatingMode.DAY,
        HVAC_MODE_FAN_ONLY: QuickMode.QM_VENTILATION_BOOST
    }

    _SUPPORTED_HVAC_MODE = list(set(_MODE_TO_HVAC.values()))

    _SUPPORTED_PRESET_MODE = list(set(_MODE_TO_PRESET.values()))

    def __init__(self, system: System, zone: Zone):
        """Initialize entity."""
        super().__init__(system, zone.id, zone.name, zone)
        self._active_mode = system.get_active_mode_zone(zone)
        self._supported_features = SUPPORT_TARGET_TEMPERATURE_RANGE \
            | SUPPORT_TARGET_TEMPERATURE \
            | SUPPORT_PRESET_MODE

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        return self._MODE_TO_HVAC[self._active_mode.current_mode]

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes."""
        return self._SUPPORTED_HVAC_MODE

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp."""
        return self._MODE_TO_PRESET[self._active_mode.current_mode]

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes."""
        return self._SUPPORTED_PRESET_MODE

    def set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if PRESET_AWAY == preset_mode:
            self.hub.set_zone_operation_mode(self, self._component,
                                             HeatingMode.OFF.name)
        else:
            self.hub.set_zone_operation_mode(self, self._component,
                                             HeatingMode.AUTO.name)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._supported_features

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return Zone.MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return Zone.MAX_TEMP

    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        _LOGGER.debug("Target high temp is %s",
                      self._component.target_temperature)
        return self._component.target_temperature

    @property
    def target_temperature_low(self):
        """Return the highbound target temperature we try to reach."""
        _LOGGER.debug("Target low temp is %s",
                      self._component.target_min_temperature)
        return self._component.target_min_temperature

    def get_active_mode(self):
        """Get active mode of the climate."""
        return self._system.get_active_mode_zone(self._component)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        low_temp = kwargs.get(ATTR_TARGET_TEMP_LOW)
        high_temp = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        temp = kwargs.get(ATTR_TEMPERATURE)

        if temp and temp != self._active_mode.target_temperature:
            _LOGGER.debug("Setting target temp to %s", temp)
            self.hub.set_zone_target_temperature(self, self._component, temp)
        elif low_temp and low_temp != self._component.target_min_temperature:
            _LOGGER.debug("Setting target low temp to %s", low_temp)
            self.hub.set_zone_target_low_temperature(self, self._component,
                                                     low_temp)
        elif high_temp and high_temp != self._component.target_temperature:
            _LOGGER.debug("Setting target high temp to %s", high_temp)
            self.hub.set_zone_target_high_temperature(self, self._component,
                                                      high_temp)
        else:
            _LOGGER.debug("Nothing to do")

    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        mode = self._HVAC_TO_MODE[hvac_mode]
        self.hub.set_zone_operation_mode(self, self._component, mode)
