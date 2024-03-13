"""Energenie Power-Strip (EGPS) integration."""
from pyegps import PowerStripUSB, get_device
from pyegps.exceptions import MissingLibrary, UsbError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, IntegrationError

from .const import CONF_DEVICE_API_ID, DOMAIN

PLATFORMS = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energenie Powerstrip."""
    try:
        powerstrip: PowerStripUSB | None = get_device(entry.data[CONF_DEVICE_API_ID])

    except (MissingLibrary, UsbError) as ex:
        raise IntegrationError("Can't access usb devices.") from ex

    if powerstrip is None:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = powerstrip
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        powerstrip = hass.data[DOMAIN].pop(entry.entry_id)
        powerstrip.release()

    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return unload_ok
