"""The Energy websocket API."""
from __future__ import annotations

import asyncio
import functools
from typing import Any, Awaitable, Callable, Dict, cast

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .data import (
    DEVICE_CONSUMPTION_SCHEMA,
    HOME_CONSUMPTION_SCHEMA,
    PRODUCTION_SCHEMA,
    EnergyManager,
    EnergyPreferencesUpdate,
    async_get_manager,
)

EnergyWebSocketCommandHandler = Callable[
    [HomeAssistant, websocket_api.ActiveConnection, Dict[str, Any], "EnergyManager"],
    None,
]
AsyncEnergyWebSocketCommandHandler = Callable[
    [HomeAssistant, websocket_api.ActiveConnection, Dict[str, Any], "EnergyManager"],
    Awaitable[None],
]


@callback
def async_setup(hass: HomeAssistant) -> None:
    """Set up the energy websocket API."""
    websocket_api.async_register_command(hass, ws_get_prefs)
    websocket_api.async_register_command(hass, ws_save_prefs)


def _ws_with_manager(
    func: Any,
) -> websocket_api.WebSocketCommandHandler:
    """Decorate a function to pass in a manager."""

    @websocket_api.async_response
    @functools.wraps(func)
    async def with_manager(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
    ) -> None:
        manager = await async_get_manager(hass)

        result = func(hass, connection, msg, manager)

        if asyncio.iscoroutine(result):
            await result

    return with_manager


@websocket_api.websocket_command(
    {
        vol.Required("type"): "energy/get_prefs",
    }
)
@_ws_with_manager
@callback
def ws_get_prefs(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
    manager: EnergyManager,
) -> None:
    """Handle get prefs command."""
    if manager.data is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "No prefs")
        return

    connection.send_result(msg["id"], manager.data)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "energy/save_prefs",
        vol.Optional("currency"): str,
        vol.Optional("home_consumption"): vol.Any(None, [HOME_CONSUMPTION_SCHEMA]),
        vol.Optional("device_consumption"): vol.Any(None, [DEVICE_CONSUMPTION_SCHEMA]),
        vol.Optional("production"): vol.Any(None, [PRODUCTION_SCHEMA]),
    }
)
@_ws_with_manager
@callback
def ws_save_prefs(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
    manager: EnergyManager,
) -> None:
    """Handle get prefs command."""
    msg_id = msg.pop("id")
    msg.pop("type")
    manager.async_update(cast(EnergyPreferencesUpdate, msg))
    connection.send_result(msg_id, manager.data)
