"""Platform for Mazda climate integration."""
from typing import Any

from pymazda import Client as MazdaAPIClient

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_HALVES,
    PRECISION_WHOLE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.temperature import convert as convert_temperature

from . import MazdaEntity
from .const import DATA_CLIENT, DATA_COORDINATOR, DATA_REGION, DOMAIN

PRESET_DEFROSTER_OFF = "Defroster Off"
PRESET_DEFROSTER_FRONT = "Front Defroster"
PRESET_DEFROSTER_REAR = "Rear Defroster"
PRESET_DEFROSTER_FRONT_AND_REAR = "Front and Rear Defroster"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    client = entry_data[DATA_CLIENT]
    coordinator = entry_data[DATA_COORDINATOR]
    region = entry_data[DATA_REGION]

    async_add_entities(
        MazdaClimateEntity(client, coordinator, index, region)
        for index, data in enumerate(coordinator.data)
        if data["isElectric"]
    )


class MazdaClimateEntity(MazdaEntity, ClimateEntity):
    """Class for the climate entity."""

    _attr_name = "Climate"
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_hvac_modes = [HVACMode.HEAT_COOL, HVACMode.OFF]
    _attr_preset_modes = [
        PRESET_DEFROSTER_OFF,
        PRESET_DEFROSTER_FRONT,
        PRESET_DEFROSTER_REAR,
        PRESET_DEFROSTER_FRONT_AND_REAR,
    ]

    _hvac_mode: HVACMode
    _target_temperature: float
    _preset_mode: str

    def __init__(
        self,
        client: MazdaAPIClient,
        coordinator: DataUpdateCoordinator,
        index: int,
        region: str,
    ) -> None:
        """Initialize Mazda climate entity."""
        super().__init__(client, coordinator, index)

        self.region = region
        self._attr_unique_id = self.vin

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        # Whenever a coordinator update happens, update the state of the climate entity.
        self.async_on_remove(
            self.coordinator.async_add_listener(self._update_hvac_state)
        )

        # Perform an initial update of the state.
        self._update_hvac_state()

    def _update_hvac_state(self):
        hvac_on = self.client.get_assumed_hvac_mode(self.vehicle_id)
        self._hvac_mode = HVACMode.HEAT_COOL if hvac_on else HVACMode.OFF

        hvac_setting = self.client.get_assumed_hvac_setting(self.vehicle_id)
        self._target_temperature = hvac_setting.get("temperature")

        front_defroster = hvac_setting.get("frontDefroster")
        rear_defroster = hvac_setting.get("rearDefroster")
        if front_defroster and rear_defroster:
            self._preset_mode = PRESET_DEFROSTER_FRONT_AND_REAR
        elif front_defroster:
            self._preset_mode = PRESET_DEFROSTER_FRONT
        elif rear_defroster:
            self._preset_mode = PRESET_DEFROSTER_REAR
        else:
            self._preset_mode = PRESET_DEFROSTER_OFF

        self.async_write_ha_state()

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC setting."""
        return self._hvac_mode

    @property
    def precision(self) -> float:
        """Return the precision of the temperature setting."""
        if self.data["hvacSetting"]["temperatureUnit"] == "F":
            return PRECISION_WHOLE
        return PRECISION_HALVES

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        current_temperature_celsius = self.data["evStatus"]["hvacInfo"][
            "interiorTemperatureCelsius"
        ]
        if self.data["hvacSetting"]["temperatureUnit"] == "F":
            return convert_temperature(
                current_temperature_celsius, TEMP_CELSIUS, TEMP_FAHRENHEIT
            )
        return current_temperature_celsius

    @property
    def target_temperature(self) -> float:
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        if self.data["hvacSetting"]["temperatureUnit"] == "F":
            return TEMP_FAHRENHEIT
        return TEMP_CELSIUS

    @property
    def min_temp(self) -> float:
        """Return the minimum target temperature."""
        if self.data["hvacSetting"]["temperatureUnit"] == "F":
            return 61.0
        if self.region == "MJO":
            return 18.5
        return 15.5

    @property
    def max_temp(self) -> float:
        """Return the maximum target temperature."""
        if self.data["hvacSetting"]["temperatureUnit"] == "F":
            return 83.0
        if self.region == "MJO":
            return 31.5
        return 28.5

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode based on the state of the defrosters."""
        return self._preset_mode

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set a new HVAC mode."""
        if hvac_mode == HVACMode.HEAT_COOL:
            await self.client.turn_on_hvac(self.vehicle_id)
        elif hvac_mode == HVACMode.OFF:
            await self.client.turn_off_hvac(self.vehicle_id)

        self._update_hvac_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            precision = self.precision
            rounded_temperature = round(temperature / precision) * precision

            await self.client.set_hvac_setting(
                self.vehicle_id,
                rounded_temperature,
                self.data["hvacSetting"]["temperatureUnit"],
                self._preset_mode
                in [
                    PRESET_DEFROSTER_FRONT_AND_REAR,
                    PRESET_DEFROSTER_FRONT,
                ],
                self._preset_mode
                in [
                    PRESET_DEFROSTER_FRONT_AND_REAR,
                    PRESET_DEFROSTER_REAR,
                ],
            )

            self._update_hvac_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Turn on/off the front/rear defrosters according to the chosen preset mode."""
        front_defroster = preset_mode in [
            PRESET_DEFROSTER_FRONT_AND_REAR,
            PRESET_DEFROSTER_FRONT,
        ]
        rear_defroster = preset_mode in [
            PRESET_DEFROSTER_FRONT_AND_REAR,
            PRESET_DEFROSTER_REAR,
        ]

        await self.client.set_hvac_setting(
            self.vehicle_id,
            self._target_temperature,
            self.data["hvacSetting"]["temperatureUnit"],
            front_defroster,
            rear_defroster,
        )

        self._update_hvac_state()
