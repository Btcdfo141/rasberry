"""Config flow for epson integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME

from . import validate_projector
from .const import DOMAIN
from .exceptions import CannotConnect, PoweredOff

DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_HOST): str, vol.Required(CONF_NAME, default=DOMAIN): str}
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for epson."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        for entry in self._async_current_entries(include_ignore=True):
            if import_config[CONF_HOST] == entry.data[CONF_HOST]:
                return self.async_abort(reason="already_configured")
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                projector = await validate_projector(self.hass, user_input[CONF_HOST])
                serial_no = await projector.get_serial_number()
                await self.async_set_unique_id(serial_no)
                self._abort_if_unique_id_configured()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except PoweredOff:
                _LOGGER.warning(
                    "You need to turn ON projector for initial configuration"
                )
                errors["base"] = "powered_off"
            else:
                return self.async_create_entry(
                    title=user_input.pop(CONF_NAME), data=user_input
                )
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
