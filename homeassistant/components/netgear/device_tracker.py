"""Support for Netgear routers."""
import logging

import voluptuous as vol

from homeassistant.components.device_tracker import PLATFORM_SCHEMA, SOURCE_TYPE_ROUTER
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_DEVICES,
    CONF_EXCLUDE,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import HomeAssistantType

from .const import DEVICE_ICONS, DOMAIN
from .router import async_setup_netgear_entry, NetgearRouter, NetgearDeviceEntity

_LOGGER = logging.getLogger(__name__)

CONF_APS = "accesspoints"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_HOST): cv.string,
        vol.Optional(CONF_SSL): cv.boolean,
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PORT): cv.port,
        vol.Optional(CONF_DEVICES, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_EXCLUDE, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_APS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)


async def async_get_scanner(hass, config):
    """Import Netgear configuration from YAML."""
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config,
        )
    )

    _LOGGER.warning(
        "Your Netgear configuration has been imported into the UI, "
        "please remove it from configuration.yaml. "
        "Loading Netgear via platform setup is now deprecated"
    )

    return None


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up device tracker for Netgear component."""
    def generate_classes(router: NetgearRouter, device):
        classes = []
        classes.append(NetgearScannerEntity(router, device))
        return classes
    await async_setup_netgear_entry(hass, entry, async_add_entities, generate_classes)


class NetgearScannerEntity(NetgearDeviceEntity, ScannerEntity):
    """Representation of a device connected to a Netgear router."""

    def __init__(self, router: NetgearRouter, device) -> None:
        """Initialize a Netgear device."""
        super().__init__(router, device)
        self._hostname = self.get_hostname(device)
        self._icon = DEVICE_ICONS.get(device["device_type"], "mdi:help-network")
        self._attrs = {}

    def get_hostname(self, device):
        """Return the hostname of the given device or None if we don't know."""
        hostname = device["name"]
        if hostname == "--":
            return None

        return hostname

    @callback
    def async_update_device(self) -> None:
        """Update the Netgear device."""
        self._device = self._router.devices[self._mac]
        self._active = self._device["active"]
        self._icon = DEVICE_ICONS.get(self._device["device_type"], "mdi:help-network")
        self._attrs = {
            "link_type": self._device["type"],
            "link_rate": self._device["link_rate"],
            "signal_strength": self._device["signal"],
        }
        if not self._active:
            self._attrs = {}

        self.async_write_ha_state()

    @property
    def is_connected(self):
        """Return true if the device is connected to the router."""
        return self._active

    @property
    def source_type(self) -> str:
        """Return the source type."""
        return SOURCE_TYPE_ROUTER

    @property
    def ip_address(self) -> str:
        """Return the IP address."""
        return self._device["ip"]

    @property
    def mac_address(self) -> str:
        """Return the mac address."""
        return self._mac

    @property
    def hostname(self) -> str:
        """Return the hostname."""
        return self._hostname

    @property
    def icon(self) -> str:
        """Return the icon."""
        return self._icon

    @property
    def device_state_attributes(self):
        """Return the attributes."""
        return self._attrs
