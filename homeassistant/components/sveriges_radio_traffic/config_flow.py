"""Config flow for Sveriges Radio Traffic integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import AREAS, CONF_AREA, DOMAIN, TITLE

_LOGGER = logging.getLogger(__name__)


# Should fix: adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_AREA, default="none"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=AREAS,
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="area",
            )
        ),
    }
)


class PlaceholderHub:
    """Placeholder class to make tests pass.

    Should fix: Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self) -> None:
        """Initialize."""

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        return True


async def validate_input(_, __) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    # Return info that you want to store in the config entry.
    return {"title": "Traffic information"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sveriges Radio Traffic."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry=config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                user_input[CONF_NAME] = TITLE
                return self.async_create_entry(title=TITLE, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class OptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    """Handle SR area options."""

    def __init__(self, config_entry) -> None:
        """Init stuff."""
        super().__init__(config_entry=config_entry)
        self._attr_config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage SR area options."""
        errors: dict[str, Any] = {}

        if user_input is not None:
            if not (_filter := user_input.get(CONF_AREA)) or _filter == "":
                user_input[CONF_AREA] = None
            user_input[CONF_NAME] = TITLE
            return self.async_create_entry(title=TITLE, data=user_input)

        return self.async_show_form(
            step_id="init", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
