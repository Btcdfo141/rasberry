"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

# Consider making key & name constants
# NOTE: keys must match those in the data dictionary
SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="co2",
        name="CO2",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


# async_setup_platform was generated by the scaffold, but in other components I see
# only async_setup_entry. TODO: understand the difference
# async def async_setup_platform(
#     hass: HomeAssistant,
#     config: ConfigType,
#     👆 pregenerated but does not have entry_id attribute
#     async_add_entities: AddEntitiesCallback,
#     discovery_info: DiscoveryInfoType | None = None,
# )->None:
#     pass
async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities based on a config entry."""
    # NOTE: In other components this function is called async_setup_entry

    coordinator = hass.data[DOMAIN][config.entry_id]
    # Once the coordinator is instantiated, it does the first refresh / fetches the data
    # for the first time (right?). If so I can iterate the keys of the data, and compare
    # them to SENSOR_TYPES (keys?)
    # TODO: fetch the list of sensors from the AirQ object and iterate over them
    # For that I need to access the api here. Does it mean, I need to store the
    # AirQ object in hass.data[DOMAIN][config.entry_id] instead of the coordinator?..
    # Or define a custom coordinator which references the API?
    # This is done in airly, airzone and
    # https://developers.home-assistant.io/docs/integration_fetching_data?_highlight=dataupdatecoo#coordinated-single-api-poll-for-data-for-all-entities)
    # TODO: define own coordinator
    entities = [AirQSensor(coordinator, description) for description in SENSOR_TYPES]
    async_add_entities(entities)


class AirQSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize a single sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        # TODO: check the requirements for these two fields
        self._attr_name = f"AirQ {description.name}"
        self._attr_unique_id = f"airq_{description.key}"

    # TODO: check the guidelines on properties vs attributes...
    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        # airthings has a neat way of doing it when the data returned by the API
        # are a dictionary with keys for each device, and values being dictionaries
        # of sensor values. Under this condition, the call should be:
        # self._attr_native_value = self.coordinator.data[self._id].sensors[self.entity_description.key]
        # In our case now, only one device is allowed and self.coordinator.data
        # contains the regular dict retrieved from a single device
        self._attr_native_value = self.coordinator.data[self.entity_description.key]
