"""Support for Hydrawise sprinkler binary sensors."""
from __future__ import annotations

from hydrawiser.core import Hydrawiser
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    PLATFORM_SCHEMA,
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MONITORED_CONDITIONS
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER
from .coordinator import HydrawiseDataUpdateCoordinator
from .entity import HydrawiseEntity

BINARY_SENSOR_STATUS = BinarySensorEntityDescription(
    key="status",
    name="Status",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
)

BINARY_SENSOR_IS_WATERING = BinarySensorEntityDescription(
    key="is_watering",
    name="Watering",
    device_class=BinarySensorDeviceClass.MOISTURE,
)

BINARY_SENSOR_KEYS: list[str] = [
    desc.key for desc in (BINARY_SENSOR_STATUS, BINARY_SENSOR_IS_WATERING)
]

# Deprecated since Home Assistant 2023.7.0
# Can be removed completely in 2023.10.0
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_MONITORED_CONDITIONS, default=BINARY_SENSOR_KEYS): vol.All(
            cv.ensure_list, [vol.In(BINARY_SENSOR_KEYS)]
        )
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hydrawise binary_sensor platform."""
    coordinator: HydrawiseDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]
    hydrawise: Hydrawiser = coordinator.api

    entities = [
        HydrawiseBinarySensor(
            data=hydrawise.current_controller,
            coordinator=coordinator,
            description=BINARY_SENSOR_STATUS,
        )
    ]

    # create a sensor for each zone
    for zone in hydrawise.relays:
        entities.append(
            HydrawiseBinarySensor(
                data=zone,
                coordinator=coordinator,
                description=BINARY_SENSOR_IS_WATERING,
            )
        )

    async_add_entities(entities)


class HydrawiseBinarySensor(HydrawiseEntity, BinarySensorEntity):
    """A sensor implementation for Hydrawise device."""

    @callback
    def _handle_coordinator_update(self) -> None:
        """Get the latest data and updates the state."""
        LOGGER.debug("Updating Hydrawise binary sensor: %s", self.name)
        if self.entity_description.key == "status":
            self._attr_is_on = self.coordinator.api.status == "All good!"
        elif self.entity_description.key == "is_watering":
            relay_data = self.coordinator.api.relays[self.data["relay"] - 1]
            self._attr_is_on = relay_data["timestr"] == "Now"
        super()._handle_coordinator_update()
