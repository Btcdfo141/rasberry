"""Support for the Airzone diagnostics."""
from __future__ import annotations

from typing import Any

from aioairzone.const import API_MAC

from homeassistant.components.diagnostics.util import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import AirzoneUpdateCoordinator

TO_REDACT = [
    API_MAC,
]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: AirzoneUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    diagnostics_data = {
        "info": async_redact_data(config_entry.data, TO_REDACT),
        "data": async_redact_data(coordinator.data, TO_REDACT),
    }

    return diagnostics_data
