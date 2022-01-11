"""Support for SleepIQ SleepNumber firmness and actuator number entities."""

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from . import DATA_SLEEPIQ, SleepIQDataUpdateCoordinator, SleepIQEntity
from .const import (
    ACTUATOR,
    ATTRIBUTES,
    BED,
    DEFAULT_SCAN_INTERVAL,
    FOOT,
    HEAD,
    NAME,
    RIGHT,
    SENSOR_TYPES,
    SIDES,
    SLEEP_NUMBER,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SleepIQ bed sensors."""
    coordinator = hass.data[DATA_SLEEPIQ].coordinators[config_entry.data[CONF_USERNAME]]
    sleep_number_entities = []
    actuator_entities = []

    for bed_id in coordinator.data:
        single = coordinator.foundation_features.single

        for side in SIDES:
            if getattr(coordinator.data[bed_id][BED], side) is not None:
                sleep_number_entities.append(
                    SleepIQFirmnessNumber(coordinator, bed_id, side)
                )

            # For split foundations, create head and foot actuators for each side
            if not single:
                actuator_entities.append(
                    SleepIQFoundationActuator(coordinator, bed_id, side, HEAD, single)
                )

        # For single foundations (not split), only create a one head actuator.
        # It doesn't matter which side is passed to the entity, either one will properly
        # control it
        if single:
            actuator_entities.append(
                SleepIQFoundationActuator(coordinator, bed_id, RIGHT, HEAD, single)
            )

        # Foot control will never be split, always create one entity
        # Again, the side doesn't matter
        if coordinator.foundation_features.hasFootControl:
            actuator_entities.append(
                SleepIQFoundationActuator(coordinator, bed_id, RIGHT, FOOT, True)
            )

    async_add_entities(sleep_number_entities, True)
    async_add_entities(actuator_entities, True)


class SleepIQFirmnessNumber(SleepIQEntity, NumberEntity):
    """Implementation of a SleepIQ Firmness number entity."""

    _attr_max_value: float = 100
    _attr_min_value: float = 5
    _attr_step: float = 5

    def __init__(
        self,
        coordinator: SleepIQDataUpdateCoordinator,
        bed_id: str,
        side: str,
    ) -> None:
        """Initialize the SleepIQ firmness number."""
        super().__init__(coordinator, bed_id, side)
        self._name = SLEEP_NUMBER
        self.client = coordinator.client
        self._no_updates_until = dt_util.utcnow()
        self._sleep_number = self._side.sleep_number

    @callback
    def _update_callback(self):
        """Call update method."""
        if self._no_updates_until > dt_util.utcnow():
            return

        self._sleep_number = self._side.sleep_number
        self.async_write_ha_state()

    @property
    def value(self) -> float:
        """Return the sleep number."""
        return self._sleep_number

    async def async_set_value(self, value: float) -> None:
        """Set new sleep number."""
        if await self.hass.async_add_executor_job(
            self.client.set_sleepnumber, self.side, value, self.bed_id
        ):
            self._sleep_number = value
            self._no_updates_until = dt_util.utcnow() + DEFAULT_SCAN_INTERVAL
            self.async_write_ha_state()


class SleepIQFoundationActuator(SleepIQEntity, NumberEntity):
    """Implementation of a SleepIQ foundation actuator."""

    _attr_max_value: float = 100
    _attr_min_value: float = 0
    _attr_step: float = 1

    def __init__(
        self,
        coordinator: SleepIQDataUpdateCoordinator,
        bed_id: str,
        side: str,
        actuator: str,
        single: bool,
    ) -> None:
        """Initialize the SleepIQ foundation actuator."""
        super().__init__(coordinator, bed_id, side)
        self._name = ACTUATOR if single else f"{side}_{ACTUATOR}"
        self.actuator = actuator
        self.client = coordinator.client
        self.single = single
        self._no_updates_until = dt_util.utcnow()
        self._position = getattr(self._foundation, ATTRIBUTES[side][actuator])

    @callback
    def _update_callback(self):
        """Call update method."""
        if self._no_updates_until > dt_util.utcnow():
            return

        self._position = getattr(self._foundation, ATTRIBUTES[self.side][self.actuator])
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity."""
        unique_id = f"{self.bed_id}_{self._side.sleeper.first_name}"
        if not self.single:
            unique_id += f"_{self.side}"
        return f"{unique_id}_{self.actuator}"

    @property
    def name(self) -> str:
        """Return name for the entity."""
        name = f"{NAME} {self._bed.name}"
        if not self.single:
            name += f" {self._side.sleeper.first_name}"
        return f"{name} {self.actuator} {SENSOR_TYPES[ACTUATOR]}"

    @property
    def value(self) -> float:
        """Return the foundation actuator position."""
        return self._position

    async def async_set_value(self, value: float) -> None:
        """Set new actuator position."""
        if await self.hass.async_add_executor_job(
            self.client.set_foundation_position,
            self.side,
            self.actuator,
            value,
            self.bed_id,
        ):
            self._position = value
            self._no_updates_until = dt_util.utcnow() + DEFAULT_SCAN_INTERVAL
            self.async_write_ha_state()
