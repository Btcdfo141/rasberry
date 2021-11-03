"""Support for HUE lights."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bridge import HueBridge
from .const import DOMAIN
from .v1.light import async_setup_entry as setup_entry_v1
from .v2.group import async_setup_entry as setup_groups_entry_v2
from .v2.light import async_setup_entry as setup_entry_v2


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Redirect HUE Platform setup from Config Entry to correct version."""
    bridge: HueBridge = hass.data[DOMAIN][config_entry.entry_id]

    if bridge.api_version == 1:
        return await setup_entry_v1(hass, config_entry, async_add_entities)

    await setup_entry_v2(hass, config_entry, async_add_entities)
    if bridge.allow_groups:
        # allow creating of lights for hue groups
        await setup_groups_entry_v2(hass, config_entry, async_add_entities)
