"""Data update coordinator for the Proximity integration."""

from dataclasses import dataclass
import logging
from typing import TypedDict

from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_DEVICES,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_ZONE,
    UnitOfLength,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.location import distance
from homeassistant.util.unit_conversion import DistanceConverter

from .const import (
    ATTR_DIR_OF_TRAVEL,
    ATTR_DIST_TO,
    ATTR_DIST_TO_CONVERTED,
    ATTR_NEAREST,
    CONF_IGNORED_ZONES,
    CONF_TOLERANCE,
    DEFAULT_DIR_OF_TRAVEL,
    DEFAULT_DIST_TO_ZONE,
    DEFAULT_NEAREST,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class StateChangedData:
    """StateChangedData class."""

    entity_id: str
    old_state: State | None
    new_state: State | None


class ProximityData(TypedDict):
    """ProximityData type class."""

    dist_to_zone: str | float
    dist_to_zone_converted: str | float
    dir_of_travel: str | float
    nearest: str | float


class ProximityDataUpdateCoordinator(DataUpdateCoordinator[ProximityData]):
    """Proximity data update coordinator."""

    def __init__(
        self, hass: HomeAssistant, friendly_name: str, config: ConfigType
    ) -> None:
        """Initialize the Proximity coordinator."""
        self.ignored_zones: list[str] = config[CONF_IGNORED_ZONES]
        self.proximity_devices: list[str] = config[CONF_DEVICES]
        self.tolerance: int = config[CONF_TOLERANCE]
        self.proximity_zone: str = config[CONF_ZONE]
        self.unit_of_measurement: str = config.get(
            CONF_UNIT_OF_MEASUREMENT, hass.config.units.length_unit
        )
        self.friendly_name = friendly_name

        super().__init__(
            hass,
            _LOGGER,
            name=friendly_name,
            update_interval=None,
        )

        self.data = {
            ATTR_DIST_TO: DEFAULT_DIST_TO_ZONE,
            ATTR_DIST_TO_CONVERTED: DEFAULT_DIST_TO_ZONE,
            ATTR_DIR_OF_TRAVEL: DEFAULT_DIR_OF_TRAVEL,
            ATTR_NEAREST: DEFAULT_NEAREST,
        }

        self.state_change_data: StateChangedData | None = None

    async def async_check_proximity_state_change(
        self, entity: str, old_state: State | None, new_state: State | None
    ) -> None:
        """Fetch and process state change event."""
        if new_state is None:
            _LOGGER.debug("no new_state -> abort")
            return

        self.state_change_data = StateChangedData(entity, old_state, new_state)
        await self.async_refresh()

    def _convert(self, value: int | float) -> float:
        """Round and convert given distance value."""
        return round(
            DistanceConverter.convert(
                value,
                UnitOfLength.METERS,
                self.unit_of_measurement,
            )
        )

    async def _async_update_data(self) -> ProximityData:
        """Calculate Proximity data."""
        if (
            state_change_data := self.state_change_data
        ) is None or state_change_data.new_state is None:
            return self.data

        entity_name = state_change_data.new_state.name
        devices_to_calculate = False
        devices_in_zone = []

        zone_state = self.hass.states.get(f"zone.{self.proximity_zone}")
        proximity_latitude = (
            zone_state.attributes.get(ATTR_LATITUDE) if zone_state else None
        )
        proximity_longitude = (
            zone_state.attributes.get(ATTR_LONGITUDE) if zone_state else None
        )

        # Check for devices in the monitored zone.
        for device in self.proximity_devices:
            if (device_state := self.hass.states.get(device)) is None:
                devices_to_calculate = True
                continue

            if device_state.state not in self.ignored_zones:
                devices_to_calculate = True

            # Check the location of all devices.
            if (device_state.state).lower() == (self.proximity_zone).lower():
                device_friendly = device_state.name
                devices_in_zone.append(device_friendly)

        # No-one to track so reset the entity.
        if not devices_to_calculate:
            _LOGGER.debug("no devices_to_calculate -> abort")
            return {
                ATTR_DIST_TO: DEFAULT_DIST_TO_ZONE,
                ATTR_DIST_TO_CONVERTED: DEFAULT_DIST_TO_ZONE,
                ATTR_DIR_OF_TRAVEL: DEFAULT_DIR_OF_TRAVEL,
                ATTR_NEAREST: DEFAULT_NEAREST,
            }

        # At least one device is in the monitored zone so update the entity.
        if devices_in_zone:
            _LOGGER.debug("at least one device is in zone -> arrived")
            return {
                ATTR_DIST_TO: 0,
                ATTR_DIST_TO_CONVERTED: 0,
                ATTR_DIR_OF_TRAVEL: "arrived",
                ATTR_NEAREST: ", ".join(devices_in_zone),
            }

        # We can't check proximity because latitude and longitude don't exist.
        if "latitude" not in state_change_data.new_state.attributes:
            _LOGGER.debug("no latitude and longitude -> reset")
            return self.data

        # Collect distances to the zone for all devices.
        distances_to_zone: dict[str, float] = {}
        for device in self.proximity_devices:
            # Ignore devices in an ignored zone.
            device_state = self.hass.states.get(device)
            if not device_state or device_state.state in self.ignored_zones:
                continue

            # Ignore devices if proximity cannot be calculated.
            if "latitude" not in device_state.attributes:
                continue

            # Calculate the distance to the proximity zone.
            proximity = distance(
                proximity_latitude,
                proximity_longitude,
                device_state.attributes[ATTR_LATITUDE],
                device_state.attributes[ATTR_LONGITUDE],
            )

            # Add the device and distance to a dictionary.
            if proximity is None:
                continue
            distances_to_zone[device] = proximity

        # Loop through each of the distances collected and work out the
        # closest.
        closest_device: str | None = None
        dist_to_zone: float | None = None

        for device, zone in distances_to_zone.items():
            if not dist_to_zone or zone < dist_to_zone:
                closest_device = device
                dist_to_zone = zone

        # If the closest device is one of the other devices.
        if closest_device is not None and closest_device != state_change_data.entity_id:
            _LOGGER.debug("closest device is one of the other devices -> unknown")
            device_state = self.hass.states.get(closest_device)
            assert device_state
            return {
                ATTR_DIST_TO: round(distances_to_zone[closest_device]),
                ATTR_DIST_TO_CONVERTED: self._convert(
                    distances_to_zone[closest_device]
                ),
                ATTR_DIR_OF_TRAVEL: "unknown",
                ATTR_NEAREST: device_state.name,
            }

        # Stop if we cannot calculate the direction of travel (i.e. we don't
        # have a previous state and a current LAT and LONG).
        if (
            state_change_data.old_state is None
            or "latitude" not in state_change_data.old_state.attributes
        ):
            _LOGGER.debug("no lat and lon in old_state -> unknown")
            return {
                ATTR_DIST_TO: round(distances_to_zone[state_change_data.entity_id]),
                ATTR_DIST_TO_CONVERTED: self._convert(
                    distances_to_zone[state_change_data.entity_id]
                ),
                ATTR_DIR_OF_TRAVEL: "unknown",
                ATTR_NEAREST: entity_name,
            }

        # Reset the variables
        distance_travelled: float = 0

        # Calculate the distance travelled.
        old_distance = distance(
            proximity_latitude,
            proximity_longitude,
            state_change_data.old_state.attributes[ATTR_LATITUDE],
            state_change_data.old_state.attributes[ATTR_LONGITUDE],
        )
        new_distance = distance(
            proximity_latitude,
            proximity_longitude,
            state_change_data.new_state.attributes[ATTR_LATITUDE],
            state_change_data.new_state.attributes[ATTR_LONGITUDE],
        )
        assert new_distance is not None and old_distance is not None
        distance_travelled = round(new_distance - old_distance, 1)

        # Check for tolerance
        if distance_travelled < self.tolerance * -1:
            direction_of_travel = "towards"
        elif distance_travelled > self.tolerance:
            direction_of_travel = "away_from"
        else:
            direction_of_travel = "stationary"

        # Update the proximity entity
        dist_to: float | str
        dist_to_converted: float | str
        if dist_to_zone is not None:
            dist_to = round(dist_to_zone)
            dist_to_converted = self._convert(dist_to_zone)
        else:
            dist_to = dist_to_converted = DEFAULT_DIST_TO_ZONE

        _LOGGER.debug(
            "%s updated: distance=%s: direction=%s: device=%s",
            self.friendly_name,
            dist_to,
            direction_of_travel,
            entity_name,
        )

        return {
            ATTR_DIST_TO: dist_to,
            ATTR_DIST_TO_CONVERTED: dist_to_converted,
            ATTR_DIR_OF_TRAVEL: direction_of_travel,
            ATTR_NEAREST: entity_name,
        }
