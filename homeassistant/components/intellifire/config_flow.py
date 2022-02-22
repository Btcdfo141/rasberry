"""Config flow for IntelliFire integration."""
from __future__ import annotations

from typing import Any

from aiohttp import ClientConnectionError
from intellifire4py import AsyncUDPFireplaceFinder, IntellifireAsync
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


async def validate_host_input(host: str) -> str:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api = IntellifireAsync(host)
    await api.poll()
    ret = api.data.serial
    LOGGER.info("Found a fireplace: %s", ret)
    # Return the serial number which will be used to calculate a unique ID for the device/sensors
    return ret


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IntelliFire."""

    VERSION = 2

    def __init__(self):
        """Initialize the Config Flow Handler."""
        self._discovered_host: str = ""
        self._config_context = {}

    async def _find_fireplaces(self):
        """Perform UDP discovery."""
        fireplace_finder = AsyncUDPFireplaceFinder()
        ips = await fireplace_finder.search_fireplace(timeout=1)
        if ip := ips[0]:
            self._discovered_host = ip

    async def async_step_local_config(self, user_input=None):
        """Handle local ip configuration."""
        local_schema = vol.Schema(
            {vol.Required(CONF_HOST, default=self._discovered_host): str}
        )
        errors = {}

        if user_input is not None:
            try:
                serial = await validate_host_input(user_input[CONF_HOST])

                await self.async_set_unique_id(serial)
                # check if found before
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_HOST: self._discovered_host,
                    }
                )

                self._config_context[CONF_HOST] = user_input[CONF_HOST]

                return self.async_create_entry(
                    title="Fireplace", data=self._config_context
                )

            except (ConnectionError, ClientConnectionError):
                errors["base"] = "cannot_connect"

                return self.async_show_form(
                    step_id="local_config",
                    errors=errors,
                    description_placeholders={CONF_HOST: user_input[CONF_HOST]},
                    data_schema=vol.Schema(
                        {vol.Required(CONF_HOST, default=user_input[CONF_HOST]): str}
                    ),
                )

        return self.async_show_form(
            step_id="local_config", errors=errors, data_schema=local_schema
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Start the user flow."""

        # If the integration was not triggered by DHCP attempt a quick local discovery
        if self._discovered_host == "":
            await self._find_fireplaces()

        return await self.async_step_local_config()
