"""Config flow for Ziggo Next integration."""
from collections import OrderedDict
import logging

import voluptuous as vol
from ziggonext import ZiggoNext, ZiggoNextAuthenticationError, ZiggoNextConnectionError

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import CONF_COUNTRY_CODE, DOMAIN  # pylint: disable=unused-import

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    api = ZiggoNext(data[CONF_USERNAME], data[CONF_PASSWORD], data[CONF_COUNTRY_CODE])
    try:
        api.initialize(_LOGGER)
    except ZiggoNextConnectionError as ex:
        raise CannotConnect(ex)
    except ZiggoNextAuthenticationError as ex:
        raise InvalidAuth(ex)
    # Return info that you want to store in the config entry.
    return {"title": data[CONF_USERNAME]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ziggo Next."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_UNKNOWN

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        countries = ["nl", "ch"]
        fields = OrderedDict()
        fields[vol.Required(CONF_USERNAME)] = str
        fields[vol.Required(CONF_PASSWORD)] = str
        fields[vol.Optional(CONF_COUNTRY_CODE, default="nl")] = vol.In(list(countries))

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(fields), errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
