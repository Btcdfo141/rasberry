"""Support for Genius Hub water_heater devices."""
from typing import Awaitable, List

from homeassistant.components.water_heater import (
    WaterHeaterDevice,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_OPERATION_MODE,
)
from homeassistant.const import STATE_OFF

from . import DOMAIN, GeniusZone

STATE_AUTO = "auto"
STATE_MANUAL = "manual"

# Genius Hub HW zones support only Off, Override/Boost & Timer modes
HA_OPMODE_TO_GH = {STATE_OFF: "off", STATE_AUTO: "timer", STATE_MANUAL: "override"}
GH_STATE_TO_HA = {
    "off": STATE_OFF,
    "timer": STATE_AUTO,
    "footprint": None,
    "away": None,
    "override": STATE_MANUAL,
    "early": None,
    "test": None,
    "linked": None,
    "other": None,
}

GH_HEATERS = ["hot water temperature"]


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Genius Hub water_heater entities."""
    if discovery_info is None:
        return

    client = hass.data[DOMAIN]["client"]

    entities = [
        GeniusWaterHeater(z) for z in client.zone_objs if z.data["type"] in GH_HEATERS
    ]

    async_add_entities(entities)


class GeniusWaterHeater(GeniusZone, WaterHeaterDevice):
    """Representation of a Genius Hub water_heater device."""

    def __init__(self, boiler) -> None:
        """Initialize the water_heater device."""
        super().__init__()

        self._zone = boiler
        self._operation_list = list(HA_OPMODE_TO_GH)

        self._min_temp = 30.0
        self._max_temp = 80.0
        self._supported_features = SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE

    @property
    def operation_list(self) -> List[str]:
        """Return the list of available operation modes."""
        return self._operation_list

    @property
    def current_operation(self) -> str:
        """Return the current operation mode."""
        return GH_STATE_TO_HA[self._zone.data["mode"]]

    async def async_set_operation_mode(self, operation_mode) -> Awaitable[None]:
        """Set a new operation mode for this boiler."""
        await self._zone.set_mode(HA_OPMODE_TO_GH[operation_mode])
