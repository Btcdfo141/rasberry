"""Support gathering ted5000 and ted6000 information."""
from datetime import datetime
import logging

from tedpy import MtuType, SystemType

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from .const import COORDINATOR, DOMAIN, NAME, OPTION_DEFAULTS

_LOGGER = logging.getLogger(__name__)

SUFFIX_NOW = "_now"
SUFFIX_DAILY = "_daily"
SUFFIX_MTD = "_mtd"


def build_sensor_descs(name: str, prefix: str, stype: str, is_net: bool):
    """Return a list of sensors with given key prefix and type (Production / Consumption)."""
    if is_net:  # If the sensor represents a net energy
        total_state_class = SensorStateClass.TOTAL
    else:
        total_state_class = SensorStateClass.TOTAL_INCREASING
    return [
        SensorEntityDescription(
            key=prefix.replace("energy", "power") + SUFFIX_NOW,
            name=f"{name} Current {stype.replace('Energy', 'Power')}",
            native_unit_of_measurement=UnitOfPower.WATT,
            state_class=SensorStateClass.MEASUREMENT,
            device_class=SensorDeviceClass.POWER,
        ),
        SensorEntityDescription(
            key=prefix + SUFFIX_DAILY,
            name=f"{name} Today's {stype}",
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            state_class=total_state_class,
            device_class=SensorDeviceClass.ENERGY,
        ),
        SensorEntityDescription(
            key=prefix + SUFFIX_MTD,
            name=f"{name} Month to Date {stype}",
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            state_class=total_state_class,
            device_class=SensorDeviceClass.ENERGY,
        ),
    ]


def build_mtu_sensor_descs(name: str, stype: str, is_net: bool):
    """Return a list of mtu sensors with given key prefix and type (Production / Consumption)."""
    return [
        *build_sensor_descs(name, "mtu_energy", stype, is_net),
        SensorEntityDescription(
            key="mtu_power_voltage",
            name="{name} Voltage",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
        ),
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TED sensor platform."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = data[COORDINATOR]
    config_name = data[NAME]

    entity_registry = hass.helpers.entity_registry.async_get(hass)
    config_id = str(config_entry.unique_id)
    entities = []
    for desc in build_sensor_descs(config_name, "consumption", "Energy Usage", False):
        entities.append(TedSensor(desc, config_id, coordinator))

    if coordinator.data["type"] != SystemType.NET:
        for desc in build_sensor_descs(config_name, "net", "Net Grid Energy", True):
            entities.append(TedSensor(desc, config_id, coordinator))
        for desc in build_sensor_descs(
            config_name, "production", "Energy Production", False
        ):
            entities.append(TedSensor(desc, config_id, coordinator))

    option_entities = []

    for spyder_id, spyder in coordinator.data["spyders"].items():
        for sensor_description in build_sensor_descs(
            spyder["name"], "spyder_energy", "Energy Usage", False
        ):
            option_entities.append(
                TedBreakdownSensor(
                    "spyders",
                    spyder_id,
                    sensor_description,
                    config_id,
                    coordinator,
                )
            )

    for mtu_id, mtu in coordinator.data["mtus"].items():
        is_net = False
        if mtu["type"] == MtuType.LOAD:
            stype = "Energy Usage"
        elif mtu["type"] == MtuType.GENERATION:
            stype = "Energy Production"
        else:
            stype = "Net Grid Energy"
            is_net = True
        for sensor_description in build_mtu_sensor_descs(mtu["name"], stype, is_net):
            option_entities.append(
                TedBreakdownSensor(
                    "mtus",
                    mtu_id,
                    sensor_description,
                    config_id,
                    coordinator,
                )
            )

    for sensor in option_entities:
        option = sensor.entity_description.key
        if config_entry.options.get(option, OPTION_DEFAULTS[option]):
            entities.append(sensor)
        else:
            entity_id = entity_registry.async_get_entity_id(
                Platform.SENSOR, DOMAIN, sensor.unique_id
            )
            if entity_id:
                _LOGGER.debug("Removing entity: %s", sensor.unique_id)
                entity_registry.async_remove(entity_id)

    async_add_entities(entities)


class TedSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a Ted5000 and Ted6000 sensor."""

    def __init__(
        self,
        description: SensorEntityDescription,
        device_id: str,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{self._device_id}_{self.entity_description.key}"

        super().__init__(coordinator)

    @property
    def native_value(self) -> float:
        """Return the state of the resources."""
        key, field = self.entity_description.key.split("_")
        return getattr(self.coordinator.data.get(key), field)

    @property
    def last_reset(self) -> datetime | None:
        """Return the time when the sensor was last reset, if any."""
        if self.entity_description.state_class == SensorStateClass.TOTAL:
            if self.entity_description.key.endswith(SUFFIX_DAILY):
                return dt_util.as_utc(
                    dt_util.now().replace(hour=0, minute=0, second=0, microsecond=0)
                )
            if self.entity_description.key.endswith(SUFFIX_MTD):
                return dt_util.as_utc(
                    dt_util.now().replace(
                        day=1, hour=0, minute=0, second=0, microsecond=0
                    )
                )
        return None


class TedBreakdownSensor(TedSensor):
    """Implementation of a Ted5000 and Ted6000 mtu or spyder."""

    def __init__(
        self,
        group: str,
        position: int,
        description: SensorEntityDescription,
        device_id: str,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        sensor_id = f"{device_id}_{group}_{position}"
        self._group = group
        self._position = position
        super().__init__(description, sensor_id, coordinator)

    @property
    def native_value(self) -> float:
        """Return the state of the resources."""
        _, key, field = self.entity_description.key.split("_")
        return getattr(
            self.coordinator.data[self._group].get(self._position).get(key), field
        )
