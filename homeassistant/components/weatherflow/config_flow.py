"""Config flow for WeatherFlow."""
from __future__ import annotations

import asyncio
from asyncio import Future
from typing import Any

from pyweatherflowudp.client import EVENT_DEVICE_DISCOVERED, WeatherFlowListener
from pyweatherflowudp.errors import AddressInUseError, ListenerError

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


async def _async_can_discover_devices() -> bool:
    """Return if there are devices that can be discovered."""
    future_event: Future[bool] = asyncio.get_running_loop().create_future()

    @callback
    def _async_found(_):
        """Handle a discovered device - only need to do this once so."""

        if not future_event.done():
            future_event.set_result(True)

    async with WeatherFlowListener() as client, asyncio.timeout(10):
        try:
            client.on(EVENT_DEVICE_DISCOVERED, _async_found)
            await future_event
        except asyncio.TimeoutError:
            return False

    return True


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WeatherFlow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""

        # Only allow a single instance of integration
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # Get current discovered entries.
        in_progress = self._async_in_progress()

        if not (has_devices := in_progress):
            errors = {}
            try:
                has_devices = await _async_can_discover_devices()  # type: ignore[assignment]
            except AddressInUseError:
                errors["base"] = "address_in_use"
            except ListenerError:
                errors["base"] = "cannot_connect"

            if errors or (not has_devices and user_input is None):
                return self.async_show_form(step_id="user", errors=errors)

        if not has_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_create_entry(title="WeatherFlow", data={})
