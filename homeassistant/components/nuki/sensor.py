"""Battery sensor for the Nuki Lock."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NukiEntity
from .const import ATTR_NUKI_ID, DATA_COORDINATOR, DATA_LOCKS, DOMAIN as NUKI_DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Nuki lock sensor."""
    data = hass.data[NUKI_DOMAIN][entry.entry_id]
    coordinator = data[DATA_COORDINATOR]

    async_add_entities(
        [NukiBatterySensor(coordinator, lock) for lock in data[DATA_LOCKS]]
    )


class NukiBatterySensor(NukiEntity, SensorEntity):
    """Representation of a Nuki Lock Battery sensor."""

    _attr_has_entity_name = True

    @property
    def name(self):
        """Return the name of the lock."""
        return "Battery"

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._nuki_device.nuki_id}_battery_level"

    @property
    def device_class(self):
        """Return the device class."""
        return SensorDeviceClass.BATTERY

    @property
    def extra_state_attributes(self):
        """Return the device specific state attributes."""
        data = {
            ATTR_NUKI_ID: self._nuki_device.nuki_id,
        }
        return data

    @property
    def entity_category(self):
        """Device entity category."""
        return EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        return self._nuki_device.battery_charge

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit the value is expressed in."""
        return PERCENTAGE
