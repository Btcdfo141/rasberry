"""Light/LED support for the Skybell HD Doorbell."""
from __future__ import annotations

from typing import Any

from aioskybell.device import SkybellDevice

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    COLOR_MODE_BRIGHTNESS,
    COLOR_MODE_HS,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import homeassistant.util.color as color_util

from . import SkybellEntity
from .const import DATA_COORDINATOR, DATA_DEVICES, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Skybell switch."""
    skybell = hass.data[DOMAIN][entry.entry_id]

    lights = []
    for _ in skybell[DATA_DEVICES]:
        for device in skybell[DATA_DEVICES]:
            lights.append(
                SkybellLight(
                    skybell[DATA_COORDINATOR],
                    device,
                    entry.entry_id,
                )
            )

    async_add_entities(lights)


class SkybellLight(SkybellEntity, LightEntity):
    """A light implementation for Skybell devices."""

    _attr_supported_color_modes = {COLOR_MODE_BRIGHTNESS, COLOR_MODE_HS}

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device: SkybellDevice,
        server_unique_id: str,
    ) -> None:
        """Initialize a light for a Skybell device."""
        super().__init__(coordinator, device, server_unique_id)
        self._attr_name = device.name
        self._attr_unique_id = f"{server_unique_id}/{self.name}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if ATTR_HS_COLOR in kwargs:
            rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
            await self._device.async_set_setting(ATTR_HS_COLOR, rgb)
        elif ATTR_BRIGHTNESS in kwargs:
            level = int((kwargs[ATTR_BRIGHTNESS] * 100) / 255)
            await self._device.async_set_setting(ATTR_BRIGHTNESS, level)
        else:
            await self._device.async_set_setting(ATTR_BRIGHTNESS, 100)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self._device.async_set_setting(ATTR_BRIGHTNESS, 0)

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._device.led_intensity > 0

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return int((self._device.led_intensity * 255) / 100)

    @property
    def hs_color(self) -> tuple[float, float]:
        """Return the color of the light."""
        return color_util.color_RGB_to_hs(*self._device.led_rgb)
