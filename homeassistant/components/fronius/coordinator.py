"""DataUpdateCoordinators for the Fronius integration."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, TypeVar

from pyfronius import FroniusError

from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    SOLAR_NET_ID_POWER_FLOW,
    SOLAR_NET_ID_SYSTEM,
    FroniusDeviceInfo,
    SolarNetId,
)

if TYPE_CHECKING:
    from . import FroniusSolarNet
    from .sensor import _FroniusSensorEntity

    FroniusEntityType = TypeVar("FroniusEntityType", bound=_FroniusSensorEntity)


class FroniusCoordinatorBase(
    ABC, DataUpdateCoordinator[Dict[SolarNetId, Dict[str, Any]]]
):
    """Query Fronius endpoint and keep track of seen conditions."""

    valid_keys: list[str]

    def __init__(self, *args: Any, solar_net: FroniusSolarNet, **kwargs: Any) -> None:
        """Set up the FroniusCoordinatorBase class."""
        self.solar_net = solar_net
        # unregistered_keys are used to create entities in platform module
        self.unregistered_keys: dict[SolarNetId, set[str]] = {}
        super().__init__(*args, **kwargs)

    @abstractmethod
    async def _update_method(self) -> dict[SolarNetId, Any]:
        """Return data per solar net id from pyfronius."""

    async def _async_update_data(self) -> dict[SolarNetId, Any]:
        """Fetch the latest data from the source."""
        async with self.solar_net.coordinator_lock:
            try:
                data = await self._update_method()
            except FroniusError as err:
                raise UpdateFailed(err) from err

            for solar_net_id in data:
                if solar_net_id not in self.unregistered_keys:
                    # id seen for the first time
                    self.unregistered_keys[solar_net_id] = set(self.valid_keys)
            return data

    @callback
    def add_entities_for_seen_keys(
        self,
        async_add_entities: AddEntitiesCallback,
        entity_constructor: type[FroniusEntityType],
    ) -> None:
        """
        Add entities for received keys and registers listener for future seen keys.

        Called from a platforms `async_setup_entry`.
        """

        @callback
        def _add_entities_for_unregistered_keys() -> None:
            """Add entities for keys seen for the first time."""
            new_entities: list = []
            for solar_net_id, device_data in self.data.items():
                for key in self.unregistered_keys[solar_net_id].intersection(
                    device_data
                ):
                    new_entities.append(entity_constructor(self, key, solar_net_id))
                    self.unregistered_keys[solar_net_id].remove(key)
            if new_entities:
                async_add_entities(new_entities)

        _add_entities_for_unregistered_keys()
        self.solar_net.cleanup_callbacks.append(
            self.async_add_listener(_add_entities_for_unregistered_keys)
        )


class FroniusInverterUpdateCoordinator(FroniusCoordinatorBase):
    """Query Fronius device inverter endpoint and keep track of seen conditions."""

    valid_keys = [
        "energy_day",
        "energy_year",
        "energy_total",
        "frequency_ac",
        "current_ac",
        "current_dc",
        "current_dc_2",
        "power_ac",
        "voltage_ac",
        "voltage_dc",
        "voltage_dc_2",
        "inverter_state",
        "error_code",
        "status_code",
        "led_state",
        "led_color",
    ]

    def __init__(
        self, *args: Any, inverter_info: FroniusDeviceInfo, **kwargs: Any
    ) -> None:
        """Set up a Fronius inverter device scope coordinator."""
        super().__init__(*args, **kwargs)
        self.inverter_info = inverter_info

    async def _update_method(self) -> dict[SolarNetId, Any]:
        """Return data per solar net id from pyfronius."""
        data = await self.solar_net.fronius.current_inverter_data(
            self.inverter_info.solar_net_id
        )
        # wrap a single devices data in a dict with solar_net_id key for
        # FroniusCoordinatorBase _async_update_data and add_entities_for_seen_keys
        return {self.inverter_info.solar_net_id: data}


class FroniusLoggerUpdateCoordinator(FroniusCoordinatorBase):
    """Query Fronius logger info endpoint and keep track of seen conditions."""

    valid_keys = [
        "co2_factor",
        "cash_factor",
        "delivery_factor",
    ]

    async def _update_method(self) -> dict[SolarNetId, Any]:
        """Return data per solar net id from pyfronius."""
        data = await self.solar_net.fronius.current_logger_info()
        return {SOLAR_NET_ID_SYSTEM: data}


class FroniusMeterUpdateCoordinator(FroniusCoordinatorBase):
    """Query Fronius system meter endpoint and keep track of seen conditions."""

    valid_keys = [
        "current_ac_phase_1",
        "current_ac_phase_2",
        "current_ac_phase_3",
        "energy_reactive_ac_consumed",
        "energy_reactive_ac_produced",
        "energy_real_ac_minus",
        "energy_real_ac_plus",
        "energy_real_consumed",
        "energy_real_produced",
        "frequency_phase_average",
        "meter_location",
        "power_apparent_phase_1",
        "power_apparent_phase_2",
        "power_apparent_phase_3",
        "power_apparent",
        "power_factor_phase_1",
        "power_factor_phase_2",
        "power_factor_phase_3",
        "power_factor",
        "power_reactive_phase_1",
        "power_reactive_phase_2",
        "power_reactive_phase_3",
        "power_reactive",
        "power_real_phase_1",
        "power_real_phase_2",
        "power_real_phase_3",
        "power_real",
        "voltage_ac_phase_1",
        "voltage_ac_phase_2",
        "voltage_ac_phase_3",
        "voltage_ac_phase_to_phase_12",
        "voltage_ac_phase_to_phase_23",
        "voltage_ac_phase_to_phase_31",
    ]

    async def _update_method(self) -> dict[SolarNetId, Any]:
        """Return data per solar net id from pyfronius."""
        data = await self.solar_net.fronius.current_system_meter_data()
        return data["meters"]  # type: ignore[no-any-return]


class FroniusPowerFlowUpdateCoordinator(FroniusCoordinatorBase):
    """Query Fronius power flow endpoint and keep track of seen conditions."""

    valid_keys = [
        "energy_day",
        "energy_year",
        "energy_total",
        "meter_mode",
        "power_battery",
        "power_grid",
        "power_load",
        "power_photovoltaics",
        "relative_autonomy",
        "relative_self_consumption",
    ]

    async def _update_method(self) -> dict[SolarNetId, Any]:
        """Return data per solar net id from pyfronius."""
        data = await self.solar_net.fronius.current_power_flow()
        return {SOLAR_NET_ID_POWER_FLOW: data}


class FroniusStorageUpdateCoordinator(FroniusCoordinatorBase):
    """Query Fronius system storage endpoint and keep track of seen conditions."""

    valid_keys = [
        "capacity_maximum",
        "capacity_designed",
        "current_dc",
        "voltage_dc",
        "voltage_dc_maximum_cell",
        "voltage_dc_minimum_cell",
        "state_of_charge",
        "temperature_cell",
    ]

    async def _update_method(self) -> dict[SolarNetId, Any]:
        """Return data per solar net id from pyfronius."""
        data = await self.solar_net.fronius.current_system_storage_data()
        return data["storages"]  # type: ignore[no-any-return]
