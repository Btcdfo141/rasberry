"""Helper functions for Acmeda Pulse."""
from homeassistant import config_entries
from homeassistant.helpers.device_registry import async_get_registry as get_dev_reg
from homeassistant.helpers.entity_registry import async_get_registry as get_ent_reg

from .const import DOMAIN


async def remove_devices(hass, config_entry, removed_items):
    """Get items that are removed from api."""

    for entity in removed_items:
        # Device is removed from Pulse, so we remove it from Home Assistant
        await entity.async_remove()
        ent_registry = await get_ent_reg(hass)
        if entity.entity_id in ent_registry.entities:
            ent_registry.async_remove(entity.entity_id)
        dev_registry = await get_dev_reg(hass)
        device = dev_registry.async_get_device(
            identifiers={(DOMAIN, entity.device_id)}, connections=set()
        )
        if device is not None:
            dev_registry.async_update_device(
                device.id, remove_config_entry_id=config_entry.entry_id
            )


async def update_devices(hass, config_entry, api):
    """Tell hass that device info has been updated."""
    dev_registry = await get_dev_reg(hass)

    for api_item in api.values():
        # Update Device name
        device = dev_registry.async_get_device(
            identifiers={(DOMAIN, api_item.id)}, connections=set()
        )
        if device is not None:
            dev_registry.async_update_device(
                device.id, name=api_item.name,
            )


def create_config_flow(hass, host):
    """Start a config flow."""
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={"host": host},
        )
    )
