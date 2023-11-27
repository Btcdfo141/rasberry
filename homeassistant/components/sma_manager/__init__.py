"""The SMA Manager integration."""

from sma_manager_api import SMA

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

# Local Imports
from .const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_REFRESH_INTERVAL, DOMAIN

PLATFORMS: list[str] = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Configure the Integration.

    @param hass:
    @param config:
    @return:
    """

    # Save to SMA object to state machine
    data = config.data
    sma = SMA(
        data[CONF_NAME], data[CONF_HOST], data[CONF_PORT], data[CONF_REFRESH_INTERVAL]
    )

    # Check if available/ready
    if not sma.available:
        raise ConfigEntryNotReady(
            f"Timeout while connecting socket at {data[CONF_HOST]}"
        )

    hass.data.setdefault(DOMAIN, {})[config.entry_id] = sma

    # Configure platforms
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config, platform)
        )
    return True


async def async_unload_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Unload config.

    This is called when an entry/configured device is to be removed. The class
    needs to unload itself, and remove callbacks. See the classes for further
    details

    @param hass:
    @param config:
    @return:
    """

    unload_ok = await hass.config_entries.async_unload_platforms(config, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(config.entry_id)

    return unload_ok
