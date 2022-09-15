"""The Nibe Heat Pump climate."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nibe.coil import Coil
from nibe.exceptions import CoilNotFoundException

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, LOGGER, Coordinator
from .const import Series


@dataclass
class ClimateDescriptionMixin:
    """Mixin for required fields."""

    current_address: int
    setpoint_heat_address: int
    setpoint_cool_address: int
    prio_address: int
    mixing_valve_state_address: int
    active_accessory_address: int | None
    use_room_sensor_address: int
    cooling_with_room_sensor_address: int


@dataclass
class ClimateDescription(ClimateEntityDescription, ClimateDescriptionMixin):
    """Base description."""


ADDRESS_PRIO_F = 43086
ADDRESS_PRIO_S = 31029

ADDRESS_COOLING_WITH_ROOM_SENSOR_F = 47340
ADDRESS_COOLING_WITH_ROOM_SENSOR_S = 40171

CLIMATE_SYSTEMS_F = (
    ClimateDescription(
        key="s1",
        name="Climate System S1",
        current_address=40033,
        setpoint_heat_address=47398,
        setpoint_cool_address=48785,
        prio_address=ADDRESS_PRIO_F,
        mixing_valve_state_address=43096,
        active_accessory_address=None,
        use_room_sensor_address=47394,
        cooling_with_room_sensor_address=ADDRESS_COOLING_WITH_ROOM_SENSOR_F,
    ),
    ClimateDescription(
        key="s2",
        name="Climate System S2",
        current_address=40032,
        setpoint_heat_address=47397,
        setpoint_cool_address=48784,
        prio_address=ADDRESS_PRIO_F,
        mixing_valve_state_address=43095,
        active_accessory_address=47302,
        use_room_sensor_address=47393,
        cooling_with_room_sensor_address=ADDRESS_COOLING_WITH_ROOM_SENSOR_F,
    ),
    ClimateDescription(
        key="s3",
        name="Climate System S3",
        current_address=40031,
        setpoint_heat_address=47396,
        setpoint_cool_address=48783,
        prio_address=ADDRESS_PRIO_F,
        mixing_valve_state_address=43094,
        active_accessory_address=47303,
        use_room_sensor_address=47392,
        cooling_with_room_sensor_address=ADDRESS_COOLING_WITH_ROOM_SENSOR_F,
    ),
    ClimateDescription(
        key="s4",
        name="Climate System S4",
        current_address=40030,
        setpoint_heat_address=47395,
        setpoint_cool_address=48782,
        prio_address=ADDRESS_PRIO_F,
        mixing_valve_state_address=43093,
        active_accessory_address=47304,
        use_room_sensor_address=47391,
        cooling_with_room_sensor_address=ADDRESS_COOLING_WITH_ROOM_SENSOR_F,
    ),
)

CLIMATE_SYSTEMS_S = (
    ClimateDescription(
        key="s1",
        name="Climate System S1",
        current_address=30027,
        setpoint_heat_address=40207,
        setpoint_cool_address=40989,
        prio_address=ADDRESS_PRIO_S,
        mixing_valve_state_address=31034,
        active_accessory_address=None,
        use_room_sensor_address=40203,
        cooling_with_room_sensor_address=ADDRESS_COOLING_WITH_ROOM_SENSOR_S,
    ),
    ClimateDescription(
        key="s2",
        name="Climate System S2",
        current_address=30026,
        setpoint_heat_address=40206,
        setpoint_cool_address=40988,
        prio_address=ADDRESS_PRIO_S,
        mixing_valve_state_address=31033,
        active_accessory_address=None,
        use_room_sensor_address=40202,
        cooling_with_room_sensor_address=ADDRESS_COOLING_WITH_ROOM_SENSOR_S,
    ),
    ClimateDescription(
        key="s3",
        name="Climate System S3",
        current_address=30025,
        setpoint_heat_address=40205,
        setpoint_cool_address=40987,
        prio_address=ADDRESS_PRIO_S,
        mixing_valve_state_address=31032,
        active_accessory_address=None,
        use_room_sensor_address=40201,
        cooling_with_room_sensor_address=ADDRESS_COOLING_WITH_ROOM_SENSOR_S,
    ),
    ClimateDescription(
        key="s4",
        name="Climate System S4",
        current_address=30024,
        setpoint_heat_address=40204,
        setpoint_cool_address=40986,
        prio_address=ADDRESS_PRIO_S,
        mixing_valve_state_address=31031,
        active_accessory_address=None,
        use_room_sensor_address=40200,
        cooling_with_room_sensor_address=ADDRESS_COOLING_WITH_ROOM_SENSOR_S,
    ),
)

CLIMATE_SYSTEMS = {Series.F: CLIMATE_SYSTEMS_F, Series.S: CLIMATE_SYSTEMS_S}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up platform."""

    coordinator: Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    def climate_systems():
        for description in CLIMATE_SYSTEMS.get(coordinator.series, ()):
            try:
                yield Climate(coordinator, description)
            except CoilNotFoundException as exception:
                LOGGER.debug(
                    "Skipping climate: %s due to %s", description.key, exception
                )

    async_add_entities(climate_systems())


class Climate(CoordinatorEntity[Coordinator], ClimateEntity):
    """Climate entity."""

    _attr_entity_category = None
    entity_description: ClimateDescription

    def __init__(
        self,
        coordinator: Coordinator,
        entity_description: ClimateDescription,
    ) -> None:
        """Initialize entity."""
        super().__init__(
            coordinator,
            {
                entity_description.current_address,
                entity_description.setpoint_heat_address,
                entity_description.setpoint_cool_address,
                entity_description.prio_address,
                entity_description.mixing_valve_state_address,
                entity_description.active_accessory_address,
                entity_description.use_room_sensor_address,
                entity_description.cooling_with_room_sensor_address,
            },
        )
        self._attr_available = False
        self._attr_name = entity_description.name
        self._attr_unique_id = f"{coordinator.unique_id}-{entity_description.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_hvac_action = HVACAction.IDLE
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_hvac_modes = [HVACMode.HEAT_COOL, HVACMode.OFF, HVACMode.HEAT]
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.TARGET_TEMPERATURE
        )
        self._attr_target_temperature_high = None
        self._attr_target_temperature_low = None
        self._attr_target_temperature = None
        self._attr_target_temperature_step = 0.5
        self._attr_entity_registry_enabled_default = (
            entity_description.active_accessory_address is None
        )

        self._attr_max_temp = 35.0
        self._attr_min_temp = 5.0

        def _get(address: int) -> Coil:
            return coordinator.heatpump.get_coil_by_address(address)

        self._coil_current = _get(entity_description.current_address)
        self._coil_setpoint_heat = _get(entity_description.setpoint_heat_address)
        self._coil_setpoint_cool = _get(entity_description.setpoint_cool_address)
        self._coil_prio = _get(entity_description.prio_address)
        self._coil_mixing_valve_state = _get(
            entity_description.mixing_valve_state_address
        )
        if entity_description.active_accessory_address is None:
            self._coil_active_accessory_address = None
        else:
            self._coil_active_accessory_address = _get(
                entity_description.active_accessory_address
            )
        self._coil_use_room_sensor = _get(entity_description.use_room_sensor_address)
        self._coil_cooling_with_room_sensor = _get(
            entity_description.cooling_with_room_sensor_address
        )

        if self._coil_current:
            self._attr_temperature_unit = self._coil_current.unit

    def _handle_coordinator_update(self) -> None:
        if not self.coordinator.data:
            return

        self._attr_current_temperature = self.coordinator.get_coil_float(
            self._coil_current
        )

        mode = HVACMode.OFF
        if self.coordinator.get_coil_value(self._coil_use_room_sensor) == "ON":
            if (
                self.coordinator.get_coil_value(self._coil_cooling_with_room_sensor)
                == "ON"
            ):
                mode = HVACMode.HEAT_COOL
            else:
                mode = HVACMode.HEAT
        self._attr_hvac_mode = mode

        setpoint_heat = self.coordinator.get_coil_float(self._coil_setpoint_heat)
        setpoint_cool = self.coordinator.get_coil_float(self._coil_setpoint_cool)

        if mode == HVACMode.HEAT_COOL:
            self._attr_target_temperature = None
            self._attr_target_temperature_low = setpoint_heat
            self._attr_target_temperature_high = setpoint_cool
        elif mode == HVACMode.HEAT:
            self._attr_target_temperature = setpoint_heat
            self._attr_target_temperature_low = None
            self._attr_target_temperature_high = None
        else:
            self._attr_target_temperature = None
            self._attr_target_temperature_low = None
            self._attr_target_temperature_high = None

        if prio := self.coordinator.get_coil_value(self._coil_prio):
            if (
                mixing_valve_state := self.coordinator.get_coil_value(
                    self._coil_mixing_valve_state
                )
            ) and mixing_valve_state == 30:
                self._attr_hvac_action = HVACAction.IDLE
            elif prio == "HEAT":
                self._attr_hvac_action = HVACAction.HEATING
            elif prio == "COOLING":
                self._attr_hvac_action = HVACAction.COOLING
            else:
                self._attr_hvac_action = HVACAction.IDLE
        else:
            self._attr_hvac_action = None

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False

        if not self._coil_active_accessory_address:
            return True

        if active_accessory := self.coordinator.get_coil_value(
            self._coil_active_accessory_address
        ):
            return active_accessory == "ON"

        return False

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperatures."""

        hvac_mode = kwargs.get(ATTR_HVAC_MODE, self._attr_hvac_mode)

        if (temperature := kwargs.get(ATTR_TEMPERATURE, None)) is not None:
            if hvac_mode == HVACMode.HEAT:
                await self.coordinator.async_write_coil(
                    self._coil_setpoint_heat, temperature
                )
            elif hvac_mode == HVACMode.COOL:
                await self.coordinator.async_write_coil(
                    self._coil_setpoint_cool, temperature
                )
            else:
                raise HomeAssistantError(
                    f"Don't known which temperature to control for hvac mode: {self._attr_hvac_mode}"
                )

        if (temperature := kwargs.get(ATTR_TARGET_TEMP_LOW, None)) is not None:
            await self.coordinator.async_write_coil(
                self._coil_setpoint_heat, temperature
            )

        if (temperature := kwargs.get(ATTR_TARGET_TEMP_HIGH, None)) is not None:
            await self.coordinator.async_write_coil(
                self._coil_setpoint_cool, temperature
            )
