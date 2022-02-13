"""The Lidarr component."""
from __future__ import annotations

from aiopyarr.lidarr_client import LidarrClient
from aiopyarr.models.host_configuration import PyArrHostConfiguration

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MAX_RECORDS,
    CONF_UPCOMING_DAYS,
    DEFAULT_MAX_RECORDS,
    DEFAULT_NAME,
    DEFAULT_UPCOMING_DAYS,
    DOMAIN,
)
from .coordinator import LidarrDataUpdateCoordinator

PLATFORMS = [SENSOR_DOMAIN]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lidarr from a config entry."""
    if not entry.options:
        options = {
            CONF_UPCOMING_DAYS: entry.data.get(
                CONF_UPCOMING_DAYS, DEFAULT_UPCOMING_DAYS
            ),
            CONF_MAX_RECORDS: entry.data.get(CONF_MAX_RECORDS, DEFAULT_MAX_RECORDS),
        }
        hass.config_entries.async_update_entry(entry, options=options)
    host_configuration = PyArrHostConfiguration(
        api_token=entry.data[CONF_API_KEY],
        verify_ssl=entry.data[CONF_VERIFY_SSL],
        url=entry.data[CONF_URL],
    )
    api_client = LidarrClient(
        host_configuration=host_configuration,
        session=async_get_clientsession(hass, entry.data[CONF_VERIFY_SSL]),
        request_timeout=60,
    )
    coordinator = LidarrDataUpdateCoordinator(hass, host_configuration, api_client)
    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class LidarrEntity(CoordinatorEntity):
    """Defines a base Lidarr entity."""

    def __init__(
        self,
        coordinator: LidarrDataUpdateCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the Lidarr entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            configuration_url=coordinator.host_configuration.base_url,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry_id)},
            manufacturer=DEFAULT_NAME,
            name=DEFAULT_NAME,
            sw_version=coordinator.system_status.version,
        )
