"""Home Assistant component for accessing the Wallbox Portal API. The sensor component creates multiple sensors regarding wallbox performance."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_DEVICE_CLASS
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CONNECTIONS,
    CONF_ICON,
    CONF_NAME,
    CONF_SENSOR_TYPES,
    CONF_UNIT_OF_MEASUREMENT,
    DOMAIN,
)

CONF_STATION = "station"
UPDATE_INTERVAL = 30


async def async_setup_entry(hass, config, async_add_entities):
    """Create wallbox sensor entities in HASS."""
    coordinator = hass.data[DOMAIN][CONF_CONNECTIONS][config.entry_id]

    async_add_entities(
        WallboxSensor(coordinator, idx, ent, config)
        for idx, ent in enumerate(coordinator.data)
    )


class WallboxSensor(CoordinatorEntity, SensorEntity):
    """Representation of the Wallbox portal."""

    def __init__(self, coordinator, idx, ent, config):
        """Initialize a Wallbox sensor."""
        super().__init__(coordinator)
        _properties = CONF_SENSOR_TYPES[ent]

        self._name = f"{config.title} {_properties[CONF_NAME]}"
        self._icon = _properties[CONF_ICON]
        self._unit = _properties[CONF_UNIT_OF_MEASUREMENT]
        self._device_class = _properties[CONF_DEVICE_CLASS]
        self._ent = ent

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data[self._ent]

    @property
    def device_class(self):
        """Return the state of the sensor."""
        return self._device_class

    @property
    def unit_of_measurement(self):
        """Return the unit of the sensor."""
        return self._unit

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon
