"""Weather information for air and road temperature (by Trafikverket)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging

import aiohttp
from pytrafikverket.trafikverket_weather import TrafikverketWeather, WeatherStationInfo
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_API_KEY,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    DEGREE,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    LENGTH_MILLIMETERS,
    PERCENTAGE,
    SPEED_METERS_PER_SECOND,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    ConfigType,
    DiscoveryInfoType,
)
from homeassistant.util import Throttle

from .const import ATTR_ACTIVE, ATTR_MEASURE_TIME, ATTRIBUTION, CONF_STATION, DOMAIN

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)

SCAN_INTERVAL = timedelta(seconds=300)


@dataclass
class TrafikverketRequiredKeysMixin:
    """Mixin for required keys."""

    api_key: str


@dataclass
class TrafikverketSensorEntityDescription(
    SensorEntityDescription, TrafikverketRequiredKeysMixin
):
    """Describes Trafikverket sensor entity."""


SENSOR_TYPES: tuple[TrafikverketSensorEntityDescription, ...] = (
    TrafikverketSensorEntityDescription(
        key="air_temp",
        api_key="air_temp",
        name="Air temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        icon="mdi:thermometer",
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    TrafikverketSensorEntityDescription(
        key="road_temp",
        api_key="road_temp",
        name="Road temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        icon="mdi:thermometer",
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    TrafikverketSensorEntityDescription(
        key="precipitation",
        api_key="precipitationtype",
        name="Precipitation type",
        icon="mdi:weather-snowy-rainy",
        entity_registry_enabled_default=False,
    ),
    TrafikverketSensorEntityDescription(
        key="wind_direction",
        api_key="winddirection",
        name="Wind direction",
        native_unit_of_measurement=DEGREE,
        icon="mdi:flag-triangle",
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    TrafikverketSensorEntityDescription(
        key="wind_direction_text",
        api_key="winddirectiontext",
        name="Wind direction text",
        icon="mdi:flag-triangle",
    ),
    TrafikverketSensorEntityDescription(
        key="wind_speed",
        api_key="windforce",
        name="Wind speed",
        native_unit_of_measurement=SPEED_METERS_PER_SECOND,
        icon="mdi:weather-windy",
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    TrafikverketSensorEntityDescription(
        key="wind_speed_max",
        api_key="windforcemax",
        name="Wind speed max",
        native_unit_of_measurement=SPEED_METERS_PER_SECOND,
        icon="mdi:weather-windy-variant",
        entity_registry_enabled_default=False,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    TrafikverketSensorEntityDescription(
        key="humidity",
        api_key="humidity",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:water-percent",
        device_class=DEVICE_CLASS_HUMIDITY,
        entity_registry_enabled_default=False,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    TrafikverketSensorEntityDescription(
        key="precipitation_amount",
        api_key="precipitation_amount",
        name="Precipitation amount",
        native_unit_of_measurement=LENGTH_MILLIMETERS,
        icon="mdi:cup-water",
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    TrafikverketSensorEntityDescription(
        key="precipitation_amountname",
        api_key="precipitation_amountname",
        name="Precipitation name",
        icon="mdi:weather-pouring",
        entity_registry_enabled_default=False,
    ),
)

SENSOR_KEYS = [desc.key for desc in SENSOR_TYPES]

PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_STATION): cv.string,
        vol.Required(CONF_MONITORED_CONDITIONS, default=[]): [vol.In(SENSOR_KEYS)],
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType = None,
) -> None:
    """Import Trafikverket Weather configuration from YAML."""
    _LOGGER.warning(
        # Config flow added in Home Assistant Core 2021.12, remove import flow in 2022.4
        "Loading Trafikverket Weather via platform setup is deprecated; Please remove it from your configuration"
    )
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config,
        )
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Trafikverket sensor entry."""

    sensor_name = entry.data[CONF_STATION]
    sensor_api = entry.data[CONF_API_KEY]
    sensor_station = entry.data[CONF_STATION]

    web_session = async_get_clientsession(hass)

    weather_api = TrafikverketWeather(web_session, sensor_api)

    entities = [
        TrafikverketWeatherStation(
            weather_api, sensor_name, sensor_station, description
        )
        for description in SENSOR_TYPES
    ]

    async_add_entities(entities, True)


class TrafikverketWeatherStation(SensorEntity):
    """Representation of a Trafikverket sensor."""

    entity_description: TrafikverketSensorEntityDescription

    def __init__(
        self,
        weather_api: TrafikverketWeather,
        name: str,
        sensor_station: str,
        description: TrafikverketSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._attr_name = f"{name} {description.name}"
        self._attr_unique_id = f"trafikverket_{name}_{description.key}"
        self._station = sensor_station
        self._weather_api = weather_api
        self._weather: WeatherStationInfo | None = None
        self._active: bool = False
        self._measure_time: str = "1970-01-01T00:00:00"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes of Trafikverket Weatherstation."""
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_ACTIVE: self._active,
            ATTR_MEASURE_TIME: self._measure_time,
        }

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self) -> None:
        """Get the latest data from Trafikverket and updates the states."""
        try:
            self._weather = await self._weather_api.async_get_weather(self._station)
            self._attr_native_value = getattr(
                self._weather, self.entity_description.api_key
            )
        except (asyncio.TimeoutError, aiohttp.ClientError, ValueError) as error:
            _LOGGER.error("Could not fetch weather data: %s", error)
            return
        self._active = self._weather.active
        self._measure_time = self._weather.measure_time
