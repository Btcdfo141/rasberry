"""The cert_expiry component."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import callback
from homeassistant.helpers.typing import HomeAssistantType

from .const import DOMAIN


async def async_setup(hass, config):
    """Platform setup, do nothing."""
    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Load the saved entities."""
    hass.data.setdefault(DOMAIN, {})

    # store the info for later
    hass.data[DOMAIN][entry.entry_id] = entry

    @callback
    def async_start(_):
        """Load the entry after the start event."""
        for eid in hass.data[DOMAIN]:
            entry = hass.data[DOMAIN][eid]
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, "sensor")
            )
        hass.data[DOMAIN] = {}

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, async_start)

    return True
