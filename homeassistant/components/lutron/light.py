"""Support for Lutron lights."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.util import slugify

from . import DOMAIN, LutronData
from .entity import LutronDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Lutron light platform.

    Adds dimmers from the Main Repeater associated with the config_entry as
    light entities.
    """
    ent_reg = er.async_get(hass)
    entry_data: LutronData = hass.data[DOMAIN][config_entry.entry_id]

    for area_name, device in entry_data.lights:
        if device.type == "CEILING_FAN_TYPE":
            # If this is a fan check to see if this entity already exists. If not, do not create a new one.
            entity_id = f"light.{slugify(f'{area_name} {device.name}')}"
            if ent_reg.async_is_registered(entity_id):
                entity_entry = ent_reg.async_get(entity_id)
                assert entity_entry
                if entity_entry.disabled:
                    # If the entity exists and is disabled then we want to remove the entity so that the user is using the new fan entity instead.
                    ent_reg.async_remove(entity_id)
                else:
                    async_add_entities(
                        [LutronLight(area_name, device, entry_data.client)],
                        True,
                    )
                    async_create_issue(
                        hass,
                        DOMAIN,
                        "deprecated_light_fan",
                        breaks_in_ha_version="2024.7.0",
                        is_fixable=False,
                        severity=IssueSeverity.WARNING,
                        translation_key="deprecated_light_fan",
                    )
        else:
            async_add_entities(
                [LutronLight(area_name, device, entry_data.client)],
                True,
            )


def to_lutron_level(level):
    """Convert the given Home Assistant light level (0-255) to Lutron (0.0-100.0)."""
    return float((level * 100) / 255)


def to_hass_level(level):
    """Convert the given Lutron (0.0-100.0) light level to Home Assistant (0-255)."""
    return int((level * 255) / 100)


class LutronLight(LutronDevice, LightEntity):
    """Representation of a Lutron Light, including dimmable."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, area_name, lutron_device, controller) -> None:
        """Initialize the light."""
        self._prev_brightness = None
        super().__init__(area_name, lutron_device, controller)
        self._is_fan = lutron_device.type == "CEILING_FAN_TYPE"

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        new_brightness = to_hass_level(self._lutron_device.last_level())
        if new_brightness != 0:
            self._prev_brightness = new_brightness
        return new_brightness

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        if self._is_fan:
            async_create_issue(
                self.hass,
                DOMAIN,
                "deprecated_light_fan_on",
                breaks_in_ha_version="2024.7.0",
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key="deprecated_light_fan_on",
            )
        if ATTR_BRIGHTNESS in kwargs and self._lutron_device.is_dimmable:
            brightness = kwargs[ATTR_BRIGHTNESS]
        elif self._prev_brightness == 0:
            brightness = 255 / 2
        else:
            brightness = self._prev_brightness
        self._prev_brightness = brightness
        self._lutron_device.level = to_lutron_level(brightness)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        if self._is_fan:
            async_create_issue(
                self.hass,
                DOMAIN,
                "deprecated_light_fan_off",
                breaks_in_ha_version="2024.7.0",
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key="deprecated_light_fan_off",
            )
        self._lutron_device.level = 0

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the state attributes."""
        return {"lutron_integration_id": self._lutron_device.id}

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._lutron_device.last_level() > 0

    def update(self) -> None:
        """Call when forcing a refresh of the device."""
        if self._prev_brightness is None:
            self._prev_brightness = to_hass_level(self._lutron_device.level)
