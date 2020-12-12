"""Support for ASUSWRT devices."""
import asyncio
import logging

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_MODE,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_PROTOCOL,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import HomeAssistantType

from .const import (
    CONF_DNSMASQ,
    CONF_INTERFACE,
    CONF_REQUIRE_IP,
    CONF_SSH_KEY,
    DATA_ASUSWRT,
    DEFAULT_DNSMASQ,
    DEFAULT_INTERFACE,
    DEFAULT_SSH_PORT,
    DOMAIN,
    SENSOR_TYPES,
)
from .router import get_api

PLATFORMS = ["device_tracker", "sensor"]

CONF_PUB_KEY = "pub_key"
CONF_SENSORS = "sensors"
SECRET_GROUP = "Password or SSH Key"

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    vol.All(
        cv.deprecated(DOMAIN, invalidation_version="0.121"),
        {
            DOMAIN: vol.Schema(
                {
                    vol.Required(CONF_HOST): cv.string,
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Optional(CONF_PROTOCOL, default="ssh"): vol.In(
                        ["ssh", "telnet"]
                    ),
                    vol.Optional(CONF_MODE, default="router"): vol.In(["router", "ap"]),
                    vol.Optional(CONF_PORT, default=DEFAULT_SSH_PORT): cv.port,
                    vol.Optional(CONF_REQUIRE_IP, default=True): cv.boolean,
                    vol.Exclusive(CONF_PASSWORD, SECRET_GROUP): cv.string,
                    vol.Exclusive(CONF_SSH_KEY, SECRET_GROUP): cv.isfile,
                    vol.Exclusive(CONF_PUB_KEY, SECRET_GROUP): cv.isfile,
                    vol.Optional(CONF_SENSORS): vol.All(
                        cv.ensure_list, [vol.In(SENSOR_TYPES)]
                    ),
                    vol.Optional(CONF_INTERFACE, default=DEFAULT_INTERFACE): cv.string,
                    vol.Optional(CONF_DNSMASQ, default=DEFAULT_DNSMASQ): cv.string,
                }
            )
        },
    ),
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the AsusWrt integration."""
    conf = config.get(DOMAIN)
    if conf is None:
        return True

    domains_list = hass.config_entries.async_domains()
    if DOMAIN in domains_list:
        return True

    pub_key = conf.get(CONF_PUB_KEY)
    if pub_key:
        conf[CONF_SSH_KEY] = pub_key
    conf.pop(CONF_PUB_KEY, "")
    conf.pop(CONF_SENSORS, {})
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Set up AsusWrt platform."""

    api = get_api(entry.data)

    try:
        await api.connection.async_connect()
        if not api.is_connected:
            raise ConfigEntryNotReady
    except OSError as exp:
        raise ConfigEntryNotReady from exp

    hass.data[DATA_ASUSWRT] = api

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    async def async_close_connection(event):
        """Close AsusWrt connection on HA Stop."""
        if hasattr(api.connection, "disconnect"):
            await api.connection.disconnect()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_close_connection)

    return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigEntry):
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
        api = hass.data.pop(DATA_ASUSWRT)
        if hasattr(api.connection, "disconnect"):
            await api.connection.disconnect()

    return unload_ok
