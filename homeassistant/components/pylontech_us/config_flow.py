"""Config flow for pylontech_us integration."""
from __future__ import annotations

import logging

# from pickle import TRUE
from typing import Any

from pylontech import PylontechStack
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# TOODOP adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("pylontech_us_port", default="/dev/ttyUSB0"): str,
        # Port examples: "/dev/ttyUSB0", "socket://10.10.4.13:23", "rfc2217://10.10.4.13:23"
        vol.Required("pylontech_us_baud", default=115200): int,
        vol.Required("pylontech_us_battery_count", default=7): int,
    }
)


class PylontechHub:
    """Communication to Pylontech Battery stack."""

    def __init__(self, config) -> None:
        """Initialize."""
        self._config = config

    def validate_config_input(self) -> None:
        """Validate config options. Raise exception on error."""
        # If you cannot connect:
        # throw CannotConnect
        # If the authentication is wrong:
        # InvalidAuth
        # config['port']

        try:
            stack = PylontechStack(
                device=self._config["pylontech_us_port"],
                baud=self._config["pylontech_us_baud"],
                manualBattcountLimit=self._config["pylontech_us_battery_count"],
            )
            stack.update()
        except Exception as exc:
            raise CannotConnect("Connection Error, check Port and Baudrate") from exc

        if stack.battcount != self._config["pylontech_us_battery_count"]:
            self._config["pylontech_us_battery_count"] = stack.battcount
            raise CannotConnect(
                "Wrong battery count will result in slow update please count again."
            )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for pylontech_us."""

    VERSION = 1

    hub = None

    async def validate_input(self, hass: HomeAssistant, data: dict[str, Any]) -> None:
        """Validate the user input allows us to connect.

        Throws exception on connect error.
        """

        self.hub = PylontechHub(config=data)
        await hass.async_add_executor_job(self.hub.validate_config_input)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:

            errors = {}

            try:
                await self.validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="Pylontech " + user_input["pylontech_us_port"],
                    data=user_input,
                )

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
