"""Support for reading vehicle status from ConnectedCars.io."""
from typing import Any, Callable, Dict, List

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_DEVICE_CLASS,
    ATTR_NAME,
    LENGTH_KILOMETERS,
    PERCENTAGE,
    VOLT,
    VOLUME_LITERS,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType

from . import ConnectedCarsDataUpdateCoordinator
from .const import (
    ATTR_API_VEHICLE_FUELLEVEL,
    ATTR_API_VEHICLE_FUELPERCENTAGE,
    ATTR_API_VEHICLE_LICENSEPLATE,
    ATTR_API_VEHICLE_MAKE,
    ATTR_API_VEHICLE_MODEL,
    ATTR_API_VEHICLE_NAME,
    ATTR_API_VEHICLE_ODOMETER,
    ATTR_API_VEHICLE_VIN,
    ATTR_API_VEHICLE_VOLTAGE,
    ATTR_ICON,
    ATTR_IDENTIFIERS,
    ATTR_LABEL,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_UNIT,
    ATTRIBUTION,
    DOMAIN,
)

SENSOR_TYPES = {
    ATTR_API_VEHICLE_ODOMETER: {
        ATTR_DEVICE_CLASS: None,
        ATTR_ICON: "mdi:trending-up",
        ATTR_LABEL: ATTR_API_VEHICLE_ODOMETER,
        ATTR_UNIT: LENGTH_KILOMETERS,
    },
    ATTR_API_VEHICLE_FUELLEVEL: {
        ATTR_DEVICE_CLASS: None,
        ATTR_ICON: "mdi:gauge",
        ATTR_LABEL: ATTR_API_VEHICLE_FUELLEVEL,
        ATTR_UNIT: VOLUME_LITERS,
    },
    ATTR_API_VEHICLE_FUELPERCENTAGE: {
        ATTR_DEVICE_CLASS: None,
        ATTR_ICON: "mdi:gas-station",
        ATTR_LABEL: ATTR_API_VEHICLE_FUELPERCENTAGE,
        ATTR_UNIT: PERCENTAGE,
    },
    ATTR_API_VEHICLE_VOLTAGE: {
        ATTR_DEVICE_CLASS: None,
        ATTR_ICON: "mdi:flash",
        ATTR_LABEL: ATTR_API_VEHICLE_VOLTAGE,
        ATTR_UNIT: VOLT,
    },
}


async def async_setup_entry(
    hass: HomeAssistantType,
    config_entry: ConfigEntry,
    async_add_entities: Callable[[List[Entity], bool], None],
) -> None:
    """Set up Conncted Cars entities based on a config entry."""
    name = config_entry.title

    coordinator: ConnectedCarsDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    # Maybe add vin to unique id
    sensors = []
    for sensor in SENSOR_TYPES:
        unique_id = f"{config_entry.unique_id}-{sensor.lower()}"
        sensors.append(ConnectedCarsSensor(coordinator, name, sensor, unique_id))

    async_add_entities(sensors, False)


class ConnectedCarsSensor(Entity):
    """Define an Connected Cars sensor."""

    def __init__(self, coordinator, name, kind, unique_id):
        """Initialize."""
        self._name = name
        self._unique_id = unique_id
        self.kind = kind
        self._device_class = None
        self._state = None
        self._icon = None
        self._unit_of_measurement = None
        self._attrs = {ATTR_ATTRIBUTION: ATTRIBUTION}

    @property
    def name(self):
        """Return the name."""
        return f"{self.coordinator.data[ATTR_API_VEHICLE_LICENSEPLATE]} {SENSOR_TYPES[self.kind][ATTR_LABEL]}"

    @property
    def state(self):
        """Return the state."""
        self._state = self.coordinator.data[self.kind]
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attrs

    @property
    def icon(self):
        """Return the icon."""
        self._icon = SENSOR_TYPES[self.kind][ATTR_ICON]
        return self._icon

    @property
    def device_class(self):
        """Return the device_class."""
        return SENSOR_TYPES[self.kind][ATTR_DEVICE_CLASS]

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return self._unique_id

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return SENSOR_TYPES[self.kind][ATTR_UNIT]

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this Connected Car."""
        return {
            ATTR_IDENTIFIERS: {(DOMAIN, self.coordinator.data[ATTR_API_VEHICLE_VIN])},
            ATTR_NAME: self.coordinator.data[ATTR_API_VEHICLE_NAME],
            ATTR_MANUFACTURER: self.coordinator.data[ATTR_API_VEHICLE_MAKE],
            ATTR_MODEL: self.coordinator.data[ATTR_API_VEHICLE_MODEL],
        }
