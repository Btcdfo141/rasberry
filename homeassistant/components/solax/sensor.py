"""Support for Solax inverter via local API."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from solax import RealTimeAPI
from solax.inverter import InverterError
from solax.units import Units

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MANUFACTURER

DEFAULT_PORT = 80
SCAN_INTERVAL = timedelta(seconds=30)


SENSOR_DESCRIPTIONS: dict[tuple[Units, bool, bool], SensorEntityDescription] = {
    (Units.C, False, False): SensorEntityDescription(
        key=f"{Units.C}_{False}_{False}",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    (Units.KWH, False, True): SensorEntityDescription(
        key=f"{Units.KWH}_{False}_{True}",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    (Units.KWH, False, False): SensorEntityDescription(
        key=f"{Units.KWH}_{False}_{False}",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
    ),
    (Units.KWH, True, False): SensorEntityDescription(
        key=f"{Units.KWH}_{True}_{False}",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    (Units.V, False, False): SensorEntityDescription(
        key=f"{Units.V}_{False}_{False}",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    (Units.A, False, False): SensorEntityDescription(
        key=f"{Units.A}_{False}_{False}",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    (Units.W, False, False): SensorEntityDescription(
        key=f"{Units.W}_{False}_{False}",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    (Units.PERCENT, False, False): SensorEntityDescription(
        key=f"{Units.PERCENT}_{False}_{False}",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    (Units.HZ, False, False): SensorEntityDescription(
        key=f"{Units.HZ}_{False}_{False}",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    (Units.NONE, False, False): SensorEntityDescription(
        key=f"{Units.NONE}_{False}_{False}",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Entry setup."""
    api: RealTimeAPI = hass.data[DOMAIN][entry.entry_id]
    resp = await api.get_data()
    serial = resp.serial_number
    version = resp.version
    last_reset = dt_util.start_of_local_day()
    endpoint = RealTimeDataEndpoint(hass, api)
    for sensor, (idx, measurement) in api.inverter.sensor_map().items():
        description = SENSOR_DESCRIPTIONS[
            (measurement.unit, measurement.is_monotonic, measurement.storage)
        ]

        uid = f"{serial}-{idx}"
        device = Inverter(
            api.inverter.manufacturer,
            uid,
            serial,
            version,
            sensor,
            description.native_unit_of_measurement,
            description.state_class,
            description.device_class,
            last_reset if measurement.resets_daily else None,
        )
        if measurement.resets_daily:
            entry.async_on_unload(
                async_track_time_change(
                    hass=hass,
                    action=device.async_listen_for_midnight,
                    hour=0,
                    minute=0,
                    second=0,
                )
            )

        endpoint.sensors.append(device)
    async_add_entities(endpoint.sensors)
    entry.async_create_background_task(
        hass, endpoint.async_refresh(), f"solax {entry.title} initial refresh"
    )
    entry.async_on_unload(
        async_track_time_interval(hass, endpoint.async_refresh, SCAN_INTERVAL)
    )


class RealTimeDataEndpoint:
    """Representation of a Sensor."""

    def __init__(self, hass: HomeAssistant, api: RealTimeAPI) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.api = api
        self.ready = asyncio.Event()
        self.sensors: list[Inverter] = []

    async def async_refresh(self, now=None):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        try:
            api_response = await self.api.get_data()
            self.ready.set()
        except InverterError as err:
            if now is not None:
                self.ready.clear()
                return
            raise PlatformNotReady from err
        data = api_response.data
        for sensor in self.sensors:
            if sensor.key in data:
                sensor.value = data[sensor.key]
                sensor.async_schedule_update_ha_state()


class Inverter(SensorEntity):
    """Class for a sensor."""

    value: Any
    _attr_should_poll = False

    def __init__(
        self,
        manufacturer,
        uid,
        serial,
        version,
        key,
        unit,
        state_class=None,
        device_class=None,
        last_reset=None,
    ) -> None:
        """Initialize an inverter sensor."""
        self._attr_unique_id = uid
        self._attr_name = f"{manufacturer} {serial} {key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._attr_last_reset = last_reset
        self._attr_device_class = device_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer=MANUFACTURER,
            name=f"{manufacturer} {serial}",
            sw_version=version,
        )
        self.key = key
        self.value = None

    @callback
    def async_listen_for_midnight(self, today: datetime) -> None:
        """Reset at midnight."""
        self._attr_last_reset = dt_util.start_of_local_day(today)
        self.value = 0
        self.async_schedule_update_ha_state()

    @property
    def native_value(self):
        """State of this inverter attribute."""
        return self.value
