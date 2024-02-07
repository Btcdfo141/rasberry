"""Diagnostics support for myUplink."""
from __future__ import annotations

from typing import Any

from myuplink.api import MyUplinkAPI

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {"access_token", "refresh_token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    api: MyUplinkAPI = hass.data[DOMAIN][config_entry.entry_id].api
    myuplink_data = {}
    myuplink_data["my_systems"] = await api.async_get_systems_json()
    for system in myuplink_data["my_systems"]["systems"]:
        myuplink_data["my_systems"]["devices"] = []
        for device in system["devices"]:
            device_data = await api.async_get_device_json(device["id"])
            device_points = await api.async_get_device_points_json(device["id"])
            myuplink_data["my_systems"]["devices"].append(
                {system["systemId"]: device_data, "points": device_points}
            )

    diagnostics_data = {
        "config_entry_data": async_redact_data(dict(config_entry.data), TO_REDACT),
        "myuplink_data": myuplink_data,
    }

    return diagnostics_data
