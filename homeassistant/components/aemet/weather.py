"""Support for the AEMET OpenData service."""
from homeassistant.components.weather import WeatherEntity
from homeassistant.const import TEMP_CELSIUS

from .const import (
    ATTR_API_CONDITION,
    ATTR_API_FORECAST,
    ATTR_API_HUMIDITY,
    ATTR_API_PRESSURE,
    ATTR_API_TEMPERATURE,
    ATTR_API_WIND_BEARING,
    ATTR_API_WIND_SPEED,
    ATTRIBUTION,
    DOMAIN,
    ENTRY_NAME,
    ENTRY_WEATHER_COORDINATOR,
)
from .weather_update_coordinator import WeatherUpdateCoordinator


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up AEMET OpenData weather entity based on a config entry."""
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    name = domain_data[ENTRY_NAME]
    weather_coordinator = domain_data[ENTRY_WEATHER_COORDINATOR]

    unique_id = f"{config_entry.unique_id}"
    aemet_weather = AemetWeather(name, unique_id, weather_coordinator)

    async_add_entities([aemet_weather], False)


class AemetWeather(WeatherEntity):
    """Implementation of an AEMET OpenData sensor."""

    def __init__(
        self,
        name,
        unique_id,
        weather_coordinator: WeatherUpdateCoordinator,
    ):
        """Initialize the sensor."""
        self._name = name
        self._unique_id = unique_id
        self._weather_coordinator = weather_coordinator

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def available(self):
        """Return True if entity is available."""
        return self._weather_coordinator.last_update_success

    @property
    def condition(self):
        """Return the current condition."""
        return self._weather_coordinator.data[ATTR_API_CONDITION]

    @property
    def forecast(self):
        """Return the forecast array."""
        return self._weather_coordinator.data[ATTR_API_FORECAST]

    @property
    def humidity(self):
        """Return the humidity."""
        return self._weather_coordinator.data[ATTR_API_HUMIDITY]

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def pressure(self):
        """Return the pressure."""
        return self._weather_coordinator.data[ATTR_API_PRESSURE]

    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return False

    @property
    def temperature(self):
        """Return the temperature."""
        return self._weather_coordinator.data[ATTR_API_TEMPERATURE]

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return self._unique_id

    @property
    def wind_bearing(self):
        """Return the temperature."""
        return self._weather_coordinator.data[ATTR_API_WIND_BEARING]

    @property
    def wind_speed(self):
        """Return the temperature."""
        return self._weather_coordinator.data[ATTR_API_WIND_SPEED]

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self._weather_coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Get the latest data from AEMET and updates the states."""
        await self._weather_coordinator.async_request_refresh()
