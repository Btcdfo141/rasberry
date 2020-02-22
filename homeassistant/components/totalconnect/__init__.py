"""The totalconnect component."""
import asyncio
import logging

from total_connect_client import TotalConnectClient
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["alarm_control_panel", "binary_sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up from existing/saved configuration."""
    conf = config.get(DOMAIN)
    if conf is None:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up upon config entry in user interface."""
    hass.data.setdefault(DOMAIN, {})

    conf = entry.data
    username = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)

    client = TotalConnectClient.TotalConnectClient(username, password)

    if not client.is_logged_in():
        _LOGGER.error("TotalConnect authentication failed")
        return False

    hass.data[DOMAIN][username] = TotalConnectSystem(username, password, client)

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.data[CONF_USERNAME])

    return unload_ok


class TotalConnectSystem:
    """TotalConnect System class."""

    def __init__(self, username, password, client):
        """Initialize the TotalConnect system."""
        self._username = username
        self._password = password
        self.client = client
