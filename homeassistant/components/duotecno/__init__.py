"""The duotecno integration."""
from __future__ import annotations

from duotecno.controller import PyDuotecno
from duotecno.exceptions import InvallidPassword, LoadFailure

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up duotecno from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    controller = PyDuotecno()
    hass.data[DOMAIN][entry.entry_id] = controller
    try:
        await controller.connect(
            entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_PASSWORD]
        )
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except OSError as err:
        raise PlatformNotReady from err
    except InvallidPassword as err:
        raise PlatformNotReady from err
    except LoadFailure as err:
        raise PlatformNotReady from err

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
