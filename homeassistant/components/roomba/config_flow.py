"""Config flow to configure demo component."""
import asyncio
import logging

import async_timeout
from roomba import Roomba, RoombaConnectionError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback

from .const import (
    CONF_CERT,
    CONF_CONTINUOUS,
    CONF_DELAY,
    DEFAULT_CERT,
    DEFAULT_CONTINUOUS,
    DEFAULT_DELAY,
    DOMAIN,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_CERT, default=DEFAULT_CERT): str,
        vol.Optional(CONF_CONTINUOUS, default=DEFAULT_CONTINUOUS): bool,
        vol.Optional(CONF_DELAY, default=DEFAULT_DELAY): int,
    }
)

_LOGGER = logging.getLogger(__name__)


class RoombaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Demo configuration flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_import(self, import_info):
        """Set the config entry up from yaml."""
        return self.async_create_entry(title="Roomba", data={})

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}

        if user_input is not None:
            self.name = None
            self.host = user_input["host"]
            self.username = user_input["username"]
            self.password = user_input["password"]
            self.certificate = user_input["certificate"]
            self.continuous = user_input["continuous"]
            self.delay = user_input["delay"]

            roomba = Roomba(
                address=self.host,
                blid=self.username,
                password=self.password,
                cert_name=self.certificate,
                continuous=self.continuous,
                delay=self.delay,
            )
            _LOGGER.debug("Initializing communication with host %s", self.host)

            try:
                with async_timeout.timeout(10):
                    await self.hass.async_add_job(roomba.connect)
                    while not roomba.roomba_connected:
                        await asyncio.sleep(0.5)
            except RoombaConnectionError as exc:
                _LOGGER.error(f"Error: {exc}")
                errors = {"base": "cannot_connect"}
            except asyncio.TimeoutError:
                _LOGGER.error("Error: Timeout exceeded, user or password incorrect")
                # Api looping if user or password incorrect and roomba exist
                await self.hass.async_add_job(roomba.disconnect)
                errors = {"base": "invalid_auth"}

            if roomba.roomba_connected:
                self.hass.data[DOMAIN]["roomba"] = roomba
                return self.async_create_entry(
                    title=self.name,
                    data={
                        "host": self.host,
                        "username": self.username,
                        "password": self.password,
                        "certificate": self.certificate,
                        "continuous": self.continuous,
                        "delay": self.delay,
                    },
                )

        # If there was no user input, do not show the errors.
        if user_input is None:
            errors = {}

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CERT,
                        default=self.config_entry.options.get(CONF_CERT, DEFAULT_CERT),
                    ): str,
                    vol.Optional(
                        CONF_CONTINUOUS,
                        default=self.config_entry.options.get(
                            CONF_CONTINUOUS, DEFAULT_CONTINUOUS
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_DELAY,
                        default=self.config_entry.options.get(
                            CONF_DELAY, DEFAULT_DELAY
                        ),
                    ): int,
                }
            ),
        )
