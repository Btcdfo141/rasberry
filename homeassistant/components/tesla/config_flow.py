"""Tesla Config Flow."""
from collections import OrderedDict
import logging

import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    OrderedDict(
        [(vol.Required(CONF_USERNAME), str), (vol.Required(CONF_PASSWORD), str)]
    )
)


@callback
def configured_instances(hass):
    """Return a set of configured Tesla instances."""
    return set(entry.title for entry in hass.config_entries.async_entries(DOMAIN))


@config_entries.HANDLERS.register(DOMAIN)
class DomainConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tesla."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize the config flow."""
        self.login = None
        self.config = OrderedDict()
        self.data_schema = DATA_SCHEMA

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input=None):
        """Handle the start of the config flow."""

        if not user_input:
            return await self._show_form(data_schema=self.data_schema)

        if user_input[CONF_USERNAME] in configured_instances(self.hass):
            return await self._show_form(errors={CONF_USERNAME: "identifier_exists"})

        self.config[CONF_USERNAME] = user_input[CONF_USERNAME]

        try:
            info = await validate_input(self.hass, user_input)
            return self.async_create_entry(title=user_input[CONF_USERNAME], data=info)
        except CannotConnect:
            return await self._show_form(errors={"base": "connection_error"})
        except InvalidAuth:
            return await self._show_form(errors={"base": "invalid_credentials"})

    async def _show_form(
        self, step="user", placeholders=None, errors=None, data_schema=None
    ) -> None:
        """Show the form to the user."""
        data_schema = data_schema or self.data_schema
        if step == "user":
            return self.async_show_form(
                step_id=step,
                data_schema=data_schema,
                errors=errors if errors else {},
                description_placeholders=placeholders if placeholders else {},
            )


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    from teslajsonpy import Controller as teslaAPI, TeslaException

    try:
        config = {}
        websession = aiohttp_client.async_get_clientsession(hass)
        controller = teslaAPI(
            websession,
            email=data[CONF_USERNAME],
            password=data[CONF_PASSWORD],
            update_interval=300,
        )
        (config[CONF_TOKEN], config[CONF_ACCESS_TOKEN]) = await controller.connect(
            test_login=True
        )
        # config["title"] = data[CONF_USERNAME]
        _LOGGER.debug("Credentials succesfuly connected to the Tesla API.")
        return config
    except TeslaException as ex:
        if ex.code == 401:
            _LOGGER.error("Unable to communicate with Tesla API: %s", ex)
            raise InvalidAuth()
        raise CannotConnect()


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
