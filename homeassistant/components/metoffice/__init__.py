"""The Met Office integration."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODE,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    METOFFICE_COORDINATOR,
    METOFFICE_DATA,
    METOFFICE_LISTENER,
    METOFFICE_NAME,
    MODE_3HOURLY,
)
from .data import MetOfficeData

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["weather", "sensor"]


async def metoffice_data_update_listener(hass, entry):
    """Handle options update."""
    _LOGGER.debug(
        "Updating %s update mode to %s", entry.data[CONF_NAME], entry.options[CONF_MODE]
    )
    hass_data = hass.data[DOMAIN][entry.entry_id]
    if entry.options[CONF_MODE] != hass_data[METOFFICE_DATA].mode:
        hass_data[METOFFICE_DATA].mode = entry.options[CONF_MODE]
        await hass_data[METOFFICE_COORDINATOR].async_refresh()


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Met Office weather component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up a Met Office entry."""

    # need to migrate previous versions to have a mode, but also
    # ensure options set after the initial setup is preserved
    if CONF_MODE in entry.options:
        mode = entry.options[CONF_MODE]
    elif CONF_MODE in entry.data:
        mode = entry.data[CONF_MODE]
    else:
        mode = MODE_3HOURLY

    hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_MODE: mode})

    api_key = entry.data[CONF_API_KEY]
    latitude = entry.data[CONF_LATITUDE]
    longitude = entry.data[CONF_LONGITUDE]
    mode = entry.data[CONF_MODE]

    metoffice_data = MetOfficeData(hass, api_key, latitude, longitude, mode)
    await metoffice_data.async_update_site()
    if metoffice_data.site_name is None:
        raise ConfigEntryNotReady()

    metoffice_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"MetOffice Coordinator for {metoffice_data.site_name}",
        update_method=metoffice_data.async_update,
        update_interval=DEFAULT_SCAN_INTERVAL,
    )

    remove_listener = entry.add_update_listener(metoffice_data_update_listener)

    metoffice_hass_data = hass.data.setdefault(DOMAIN, {})
    metoffice_hass_data[entry.entry_id] = {
        METOFFICE_DATA: metoffice_data,
        METOFFICE_COORDINATOR: metoffice_coordinator,
        METOFFICE_NAME: metoffice_data.site_name,
        METOFFICE_LISTENER: remove_listener,
    }

    # Fetch initial data so we have data when entities subscribe
    await metoffice_coordinator.async_refresh()
    if metoffice_data.now is None:
        raise ConfigEntryNotReady()

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN][entry.entry_id][
            METOFFICE_LISTENER
        ]()  # remove the API mode listener
        hass.data[DOMAIN].pop(entry.entry_id)
        if len(hass.data[DOMAIN]) == 0:
            hass.data.pop(DOMAIN)
    return unload_ok
