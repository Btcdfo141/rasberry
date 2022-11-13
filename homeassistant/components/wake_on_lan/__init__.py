"""Support for sending Wake-On-LAN magic packets."""
import asyncio
from collections.abc import Coroutine
from functools import partial
import logging
from typing import Any

import voluptuous as vol
import wakeonlan

from homeassistant.const import (
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    Platform,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CONF_OFF_ACTION, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_MAGIC_PACKET = "send_magic_packet"

WAKE_ON_LAN_SEND_MAGIC_PACKET_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_BROADCAST_ADDRESS): cv.string,
        vol.Optional(CONF_BROADCAST_PORT): cv.port,
    }
)

SWITCH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_BROADCAST_ADDRESS): cv.string,
        vol.Optional(CONF_BROADCAST_PORT): cv.port,
        vol.Optional(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_OFF_ACTION): cv.SCRIPT_SCHEMA,
    }
)


CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(DOMAIN): vol.All(cv.ensure_list, [vol.Schema(SWITCH_SCHEMA)])},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the wake on LAN component."""
    load_coroutines: list[Coroutine[Any, Any, None]] = []
    if wol_config := config.get(DOMAIN):
        for switch_config in wol_config:
            load_coroutines.append(
                discovery.async_load_platform(
                    hass,
                    Platform.SWITCH,
                    DOMAIN,
                    switch_config,
                    config,
                )
            )

    if load_coroutines:
        await asyncio.gather(*load_coroutines)

    async def send_magic_packet(call: ServiceCall) -> None:
        """Send magic packet to wake up a device."""
        mac_address = call.data.get(CONF_MAC)
        broadcast_address = call.data.get(CONF_BROADCAST_ADDRESS)
        broadcast_port = call.data.get(CONF_BROADCAST_PORT)

        service_kwargs = {}
        if broadcast_address is not None:
            service_kwargs["ip_address"] = broadcast_address
        if broadcast_port is not None:
            service_kwargs["port"] = broadcast_port

        _LOGGER.info(
            "Send magic packet to mac %s (broadcast: %s, port: %s)",
            mac_address,
            broadcast_address,
            broadcast_port,
        )

        await hass.async_add_executor_job(
            partial(wakeonlan.send_magic_packet, mac_address, **service_kwargs)
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_MAGIC_PACKET,
        send_magic_packet,
        schema=WAKE_ON_LAN_SEND_MAGIC_PACKET_SCHEMA,
    )

    return True
