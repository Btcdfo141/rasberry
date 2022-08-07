"""Config flow for Skybell integration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aioskybell import Skybell, exceptions
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN


class SkybellFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Skybell."""

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._email: str

    async def async_step_import(self, user_input: ConfigType) -> FlowResult:
        """Import a config entry from configuration.yaml."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        return await self.async_step_user(user_input)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle a reauthorization flow request."""
        self._email = entry_data[CONF_EMAIL]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle user's reauth credentials."""
        errors = {}
        if user_input:
            password = user_input[CONF_PASSWORD]
            context = self.context["entry_id"]
            if entry := self.hass.config_entries.async_get_entry(context):
                _, error = await self._async_validate_input(self._email, password)
                if error is None:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data=entry.data | user_input,
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].lower()
            password = user_input[CONF_PASSWORD]

            user_id, error = await self._async_validate_input(email, password)
            if error is None:
                self._async_abort_entries_match({CONF_EMAIL: email})
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=email,
                    data={CONF_EMAIL: email, CONF_PASSWORD: password},
                )
            errors["base"] = error

        user_input = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=user_input.get(CONF_EMAIL)): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def _async_validate_input(self, email: str, password: str) -> tuple:
        """Validate login credentials."""
        skybell = Skybell(
            username=email,
            password=password,
            disable_cache=True,
            session=async_get_clientsession(self.hass),
        )
        try:
            await skybell.async_initialize()
        except exceptions.SkybellAuthenticationException:
            return None, "invalid_auth"
        except exceptions.SkybellException:
            return None, "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            return None, "unknown"
        return skybell.user_id, None
