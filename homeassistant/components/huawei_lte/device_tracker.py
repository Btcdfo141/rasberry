"""Support for device tracking of Huawei LTE routers."""

import logging
import re
from typing import Any, Dict, Set

import attr
from stringcase import snakecase

from homeassistant.components.device_tracker import (
    DOMAIN as DEVICE_TRACKER_DOMAIN,
    SOURCE_TYPE_ROUTER,
)
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.const import CONF_URL
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from . import HuaweiLteBaseEntity
from .const import DOMAIN, KEY_WLAN_HOST_LIST, UPDATE_SIGNAL


_LOGGER = logging.getLogger(__name__)

_NEW_DEVICE_SCAN = "new_device_scan"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up from config entry."""

    # Grab hosts list once to examine whether the initial fetch has got some data for
    # us, i.e. if wlan host list is supported. Only set up a subscription and proceed
    # with adding and tracking entities if it is.
    router = hass.data[DOMAIN].routers[config_entry.data[CONF_URL]]
    try:
        _ = router.data[KEY_WLAN_HOST_LIST]["Hosts"]["Host"]
    except KeyError:
        _LOGGER.debug("%s[%s][%s] not in data", KEY_WLAN_HOST_LIST, "Hosts", "Host")
        return

    # Set of entities we've added already
    tracked: Set[str] = set()

    # Tell parent router to grab hosts list so we can get new entities
    router.subscriptions[KEY_WLAN_HOST_LIST].add(
        f"{DEVICE_TRACKER_DOMAIN}/{_NEW_DEVICE_SCAN}"
    )

    async def _async_maybe_add_new_entities(url: str) -> None:
        """Add new entities if the update signal comes from our router."""
        if url == router.url:
            await async_add_new_entities(hass, url, async_add_entities, tracked)

    # Register to handle router data updates
    disconnect_dispatcher = async_dispatcher_connect(
        hass, UPDATE_SIGNAL, _async_maybe_add_new_entities
    )
    router.unload_handlers.append(disconnect_dispatcher)

    # Add new entities waiting to be added from initial scan
    await async_add_new_entities(hass, router.url, async_add_entities, tracked)


async def async_add_new_entities(hass, router_url, async_add_entities, tracked):
    """Add new entities."""
    router = hass.data[DOMAIN].routers[router_url]
    try:
        hosts = router.data[KEY_WLAN_HOST_LIST]["Hosts"]["Host"]
    except KeyError:
        _LOGGER.debug("%s[%s][%s] not in data", KEY_WLAN_HOST_LIST, "Hosts", "Host")
        return

    new_entities = []
    for host in (x for x in hosts if x.get("MacAddress")):
        entity = HuaweiLteScannerEntity(router, host["MacAddress"])
        if entity.unique_id in tracked:
            continue
        tracked.add(entity.unique_id)
        new_entities.append(entity)
    async_add_entities(new_entities, True)


def _better_snakecase(text: str) -> str:
    if text == text.upper():
        # All uppercase to all lowercase to get http for HTTP, not h_t_t_p
        text = text.lower()
    else:
        # Three or more consecutive uppercase with middle part lowercased
        # to get http_response for HTTPResponse, not h_t_t_p_response
        text = re.sub(
            r"([A-Z])([A-Z]+)([A-Z](?:[^A-Z]|$))",
            lambda match: f"{match.group(1)}{match.group(2).lower()}{match.group(3)}",
            text,
        )
    return snakecase(text)


@attr.s
class HuaweiLteScannerEntity(HuaweiLteBaseEntity, ScannerEntity):
    """Huawei LTE router scanner entity."""

    mac: str = attr.ib()

    _is_connected: bool = attr.ib(init=False, default=False)
    _name: str = attr.ib(init=False, default="device")
    _device_state_attributes: Dict[str, Any] = attr.ib(init=False, factory=dict)

    async def async_added_to_hass(self):
        """Subscribe to needed data on add."""
        await super().async_added_to_hass()
        self.router.subscriptions[KEY_WLAN_HOST_LIST].add(
            f"{DEVICE_TRACKER_DOMAIN}/{self.mac}"
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe from needed data on remove."""
        await super().async_will_remove_from_hass()
        self.router.subscriptions[KEY_WLAN_HOST_LIST].remove(
            f"{DEVICE_TRACKER_DOMAIN}/{self.mac}"
        )

    @property
    def _entity_name(self) -> str:
        return self._name

    @property
    def _device_unique_id(self) -> str:
        return self.mac

    @property
    def source_type(self) -> str:
        """Return SOURCE_TYPE_ROUTER."""
        return SOURCE_TYPE_ROUTER

    @property
    def is_connected(self) -> bool:
        """Get whether the entity is connected."""
        return self._is_connected

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """Get additional attributes related to entity state."""
        return self._device_state_attributes

    async def async_update(self) -> None:
        """Update state."""
        try:
            hosts = self.router.data[KEY_WLAN_HOST_LIST]["Hosts"]["Host"]
        except KeyError:
            _LOGGER.debug("%s[Hosts][Host] not in data", self.key)
            self._available = False
            return
        self._available = True

        host = next((x for x in hosts if x.get("MacAddress") == self.mac), None)
        self._is_connected = host is not None
        if self._is_connected:
            self._name = host.get("HostName", self.mac)
            self._device_state_attributes = {
                _better_snakecase(k): v
                for k, v in host.items()
                if k not in ("MacAddress", "HostName")
            }


def get_scanner(*args, **kwargs):
    """Old no longer used way to set up Huawei LTE device tracker."""
    _LOGGER.warning(
        "Loading and configuring as a platform is no longer supported or "
        "required, convert to enabling/disabling available entities"
    )
