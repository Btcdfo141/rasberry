"""Diagnostics support for Forecast.Solar integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

TO_REDACT = {
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "data": {
            "energy_production_today": coordinator.data.energy_production_today,
            "energy_production_tomorrow": coordinator.data.energy_production_tomorrow,
            "energy_current_hour": coordinator.data.energy_current_hour,
            "power_production_now": coordinator.data.power_production_now,
        },
        "account": {
            "type": coordinator.data.account_type.value,
            "rate_limit": coordinator.data.api_rate_limit,
            "timezone": coordinator.data.timezone,
        },
    }
