"""Config flow for Schlage integration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pyschlage
from pyschlage.exceptions import NotAuthorizedError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Schlage."""

    VERSION = 1

    reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            try:
                user_id = await self.hass.async_add_executor_job(
                    _authenticate, username, password
                )
            except NotAuthorizedError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unknown error")
                errors["base"] = "unknown"
            else:
                if not self.reauth_entry:
                    await self.async_set_unique_id(user_id)
                    return self.async_create_entry(title=username, data=user_input)
                if self.reauth_entry.unique_id != user_id:
                    return self.async_abort(reason="wrong_account")

                self.hass.config_entries.async_update_entry(
                    self.reauth_entry, data=user_input
                )
                await self.hass.config_entries.async_reload(self.reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle reauth upon an API authentication error."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()


def _authenticate(username: str, password: str) -> str:
    """Authenticate with the Schlage API."""
    auth = pyschlage.Auth(username, password)
    auth.authenticate()
    # The user_id property will make a blocking call if it's not already
    # cached. To avoid blocking the event loop, we read it here.
    return auth.user_id
