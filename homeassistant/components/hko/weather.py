"""Support for the HKO service."""
from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LOCATION, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    API_CONDITION,
    API_CURRENT,
    API_FORECAST,
    API_HUMIDITY,
    API_TEMPERATURE,
    ATTRIBUTION,
    DOMAIN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a HKO weather entity from a config_entry."""
    name = config_entry.data[CONF_LOCATION]
    unique_id = config_entry.unique_id
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([HKOEntity(name, unique_id, coordinator)], False)


class HKOEntity(CoordinatorEntity, WeatherEntity):
    """Define a HKO entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY
    _attr_attribution = ATTRIBUTION

    def __init__(self, name, unique_id, coordinator: DataUpdateCoordinator) -> None:
        """Initialise the weather platform."""
        super().__init__(coordinator)
        self._name = name
        self._attr_unique_id = unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.unique_id))},
            name=self.name,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def name(self) -> str:
        """Return the name."""
        return self._name

    @property
    def condition(self) -> str:
        """Return the current condition."""
        return self.coordinator.data[API_FORECAST][0][API_CONDITION]

    @property
    def native_temperature(self) -> int:
        """Return the temperature."""
        return self.coordinator.data[API_CURRENT][API_TEMPERATURE]

    @property
    def humidity(self) -> int:
        """Return the humidity."""
        return self.coordinator.data[API_CURRENT][API_HUMIDITY]

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the forecast data."""
        return self.coordinator.data[API_FORECAST]
