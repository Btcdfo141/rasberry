"""Provides diagnostics for Fully Kiosk Browser."""
from __future__ import annotations

from homeassistant.components.diagnostics.util import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

DEVICE_INFO_TO_REDACT = {
    "serial",
    "Mac",
    "ip6",
    "hostname6",
    "ip4",
    "hostname4",
    "deviceID",
    "startUrl",
    "currentPage",
}
SETTINGS_TO_REDACT = {
    "startURL",
    "mqttBrokerPassword",
    "mqttBrokerUsername",
    "remoteAdminPassword",
    "wifiKey",
    "authPassword",
    "authUsername",
    "mqttBrokerUrl",
    "kioskPin",
}


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry
) -> dict:
    """Return device diagnostics."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    data["settings"] = async_redact_data(data["settings"], SETTINGS_TO_REDACT)
    return async_redact_data(data, DEVICE_INFO_TO_REDACT)
