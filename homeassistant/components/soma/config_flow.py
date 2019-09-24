"""Config flow for Soma."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 3000


class SomaFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Instantiate config flow."""

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        if user_input is None:
            data = {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            }

            return self.async_show_form(step_id="user", data_schema=vol.Schema(data))

        return await self.async_step_creation(user_input)

    async def async_step_creation(self, user_input=None):
        """Finish config flow."""
        from api.soma_api import SomaApi

        api = SomaApi(user_input["host"], user_input["port"])
        try:
            await self.hass.async_add_executor_job(api.list_devices)
            _LOGGER.info("Successfully set up Soma Connect")
            return self.async_create_entry(
                title="Soma Connect",
                data={"host": user_input["host"], "port": user_input["port"]},
            )
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error("Connection to SOMA Connect failed.")
            return self.async_abort(reason="connection_error")

    async def async_step_import(self, user_input=None):
        """Handle flow start from existing config section."""
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason="already_setup")
        return await self.async_step_creation(user_input)
