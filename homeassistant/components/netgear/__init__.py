"""Support for Netgear routers."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.typing import HomeAssistantType

from .const import CONF_TRACKED_LIST, DOMAIN, PLATFORMS
from .router import NetgearRouter, convert_tracked_list

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up Netgear integration."""
    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Set up Netgear component."""
    router = NetgearRouter(hass, entry)
    await router.async_setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.unique_id] = router

    entry.async_on_unload(entry.add_update_listener(update_listener))

    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id)},
        manufacturer="Netgear",
        name=router.device_name,
        model=router.model,
        sw_version=router.firmware_version,
    )

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    tracked_list = convert_tracked_list(entry.options.get(CONF_TRACKED_LIST, ""))

    if tracked_list:
        # Remove entities that are no longer tracked
        entity_registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        for entity_entry in entries:
            if entity_entry.unique_id not in tracked_list:
                entity_registry.async_remove(entity_entry.entity_id)

        # Remove devices that are no longer tracked
        device_registry = dr.async_get(hass)
        devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
        for device_entry in devices:
            device_mac = dict(device_entry.connections).get("mac")
            if device_mac and device_mac not in tracked_list:
                device_registry.async_update_device(
                    device_entry.id, remove_config_entry_id=entry.entry_id
                )

    if unload_ok:
        await hass.data[DOMAIN][entry.unique_id].async_unload()
        hass.data[DOMAIN].pop(entry.unique_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
