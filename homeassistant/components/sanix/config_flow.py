"""Config flow for Sanix integration."""
import logging
from typing import Any

from sanix import Sanix
from sanix.exceptions import SanixException, SanixInvalidAuthException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_SERIAL_NO, DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL_NO): str,
        vol.Required(CONF_TOKEN): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sanix."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input:
            await self.async_set_unique_id(user_input[CONF_SERIAL_NO])
            self._abort_if_unique_id_configured()

            sanix_api = Sanix(user_input[CONF_SERIAL_NO], user_input[CONF_TOKEN])

            try:
                await self.hass.async_add_executor_job(sanix_api.fetch_data)
            except SanixInvalidAuthException:
                errors["base"] = "invalid_auth"
            except SanixException:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=MANUFACTURER,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
