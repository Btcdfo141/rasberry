"""Config flow for Picnic integration."""
from __future__ import annotations

import logging
from typing import Any

from python_frank_energie import FrankEnergie
from python_frank_energie.exceptions import AuthException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_AUTHENTICATION, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_AUTH_TOKEN, CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Frank Energie."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""

    async def async_step_login(self, user_input=None, errors=None) -> FlowResult:
        """Handle login with credentials by user."""
        if not user_input:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            )

            return self.async_show_form(
                step_id="login",
                data_schema=data_schema,
                errors=errors,
            )

        async with FrankEnergie() as api:
            try:
                auth = await api.login(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except AuthException as ex:
                _LOGGER.exception("Error during login", exc_info=ex)
                return await self.async_step_login(errors={"base": "invalid_auth"})

        data = {
            CONF_USERNAME: user_input[CONF_USERNAME],
            CONF_AUTH_TOKEN: auth.authToken,
            CONF_REFRESH_TOKEN: auth.refreshToken,
        }

        await self.async_set_unique_id(user_input[CONF_USERNAME])
        self._abort_if_unique_id_configured()

        return await self._async_create_entry(data)

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle a flow initiated by the user."""
        if not user_input:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_AUTHENTICATION): bool,
                }
            )

            return self.async_show_form(step_id="user", data_schema=data_schema)

        if user_input[CONF_AUTHENTICATION]:
            return await self.async_step_login()

        return await self._async_create_entry({})

    async def _async_create_entry(self, data: dict[str, Any]) -> FlowResult:
        await self.async_set_unique_id(data.get(CONF_USERNAME, "frank_energie"))
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=data.get(CONF_USERNAME, "Frank Energie"), data=data
        )
