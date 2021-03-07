"""Support for Netgear routers."""
import logging
from typing import Dict

import voluptuous as vol

from homeassistant.components.device_tracker import PLATFORM_SCHEMA, SOURCE_TYPE_ROUTER
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
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
from .router import NetgearRouter

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_HOST): cv.string,
        vol.Optional(CONF_SSL): cv.boolean,
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PORT): cv.port,
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_scanner(hass, config, async_add_entities, discovery_info=None):
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
        "please remove it from configuration.yaml. Loading Netgear via platform setup is now deprecated."
    )

    return True


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up device tracker for Netgear component."""
    router = hass.data[DOMAIN][entry.unique_id]
    tracked = set()

    @callback
    def update_router():
        """Update the values of the router."""
        add_entities(router, async_add_entities, tracked)

    router.listeners.append(
        async_dispatcher_connect(hass, router.signal_device_new, update_router)
    )

    update_router()


@callback
def add_entities(router, async_add_entities, tracked):
    """Add new tracker entities from the router."""
    new_tracked = []

    for mac, device in router.devices.items():
        if mac in tracked:
            continue

        new_tracked.append(NetgearDeviceEntity(router, device))
        tracked.add(mac)

    if new_tracked:
        async_add_entities(new_tracked, True)


class NetgearDeviceEntity(ScannerEntity):
    """Representation of a device connected to a Netgear router."""

    def __init__(self, router: NetgearRouter, device: Dict[str, any]) -> None:
        """Initialize a Netgear device."""
        self._router = router
        self._name = device["name"]
        self._mac = device["mac"]
        self._manufacturer = device["device_model"]
        self._icon = DEVICE_ICONS.get(device["device_type"], "mdi:help-network")
        self._active = True
        self._attrs = {}

    @callback
    def update_device(self) -> None:
        """Update the Netgear device."""
        device = self._router.devices[self._mac]
        self._active = device["active"]
        self._attrs = {
            "link_type": device["type"],
            "link_rate": device["link_rate"],
            "signal_strength": device["signal"],
        }
        if not self._active:
            self._attrs = {}

        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._mac

    @property
    def name(self) -> str:
        """Return the name."""
        return self._name

    @property
    def is_connected(self):
        """Return true if the device is connected to the router."""
        return self._active

    @property
    def source_type(self) -> str:
        """Return the source type."""
        return SOURCE_TYPE_ROUTER

    @property
    def icon(self) -> str:
        """Return the icon."""
        return self._icon

    @property
    def device_state_attributes(self) -> Dict[str, any]:
        """Return the attributes."""
        return self._attrs

    @property
    def device_info(self) -> Dict[str, any]:
        """Return the device information."""
        return {
            "connections": {(CONNECTION_NETWORK_MAC, self._mac)},
            "name": self.name,
            "manufacturer": self._manufacturer,
        }

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    async def async_added_to_hass(self):
        """Register state update callback."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self._router.signal_device_update,
                self.update_device,
            )
        )
