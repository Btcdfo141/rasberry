"""Config flow for syncthing integration."""
import logging

import aiosyncthing
import requests
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_NAME, CONF_TOKEN, CONF_URL, HTTP_FORBIDDEN

from .const import (
    CONF_VERIFY_SSL,
    DEFAULT_NAME,
    DEFAULT_URL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_URL, default=DEFAULT_URL): str,
        vol.Required(CONF_TOKEN): str,
        vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect."""

    if DOMAIN in hass.data and data[CONF_NAME] in hass.data[DOMAIN]:
        raise AlreadyConfigured

    try:
        async with aiosyncthing.Syncthing(
            data[CONF_TOKEN],
            url=data[CONF_URL],
            verify_ssl=data[CONF_VERIFY_SSL],
            loop=hass.loop,
        ) as client:
            await client.system.ping()
    except aiosyncthing.exceptions.PingError as err:
        if type(err.__cause__) is requests.exceptions.HTTPError:
            if err.__cause__.response.status_code == HTTP_FORBIDDEN:
                raise InvalidAuth
        raise CannotConnect

    return {"title": f"{DOMAIN}_{data['name']}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for syncthing."""

    VERSION = 1

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
                errors[CONF_TOKEN] = "invalid_auth"
            except AlreadyConfigured:
                errors[CONF_NAME] = "already_configured"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class AlreadyConfigured(exceptions.HomeAssistantError):
    """Error to indicate device is already configured."""
