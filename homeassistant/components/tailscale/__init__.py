"""The Tailscale integration."""
from __future__ import annotations

from tailscale import Device as TailscaleDevice

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TailscaleDataUpdateCoordinator

PLATFORMS = (BINARY_SENSOR_DOMAIN, SENSOR_DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tailscale from a config entry."""
    coordinator = TailscaleDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Tailscale config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        del hass.data[DOMAIN][entry.entry_id]
    return unload_ok


class TailscaleEntity(CoordinatorEntity):
    """Defines a Tailscale base entity."""

    device_id: str

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        device: TailscaleDevice = self.coordinator.data[self.device_id]

        configuration_url = "https://login.tailscale.com/admin/machines/"
        if device.addresses:
            configuration_url += device.addresses[0]

        return DeviceInfo(
            configuration_url=configuration_url,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, device.device_id)},
            manufacturer="Tailscale Inc.",
            model=device.os,
            name=device.hostname,
            sw_version=device.client_version,
        )
