"""Config flow for LaCrosse View integration."""
from __future__ import annotations

import logging
from typing import Any

from lacrosse_view import LaCrosse, Location, LoginError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> list[Location]:
    """Validate the user input allows us to connect."""

    api = LaCrosse(async_get_clientsession(hass))

    try:
        if not await api.login(data["username"], data["password"]):
            raise InvalidAuth

        locations: list[Location] = await api.get_locations()
        if not locations:
            raise NoLocations(
                "No locations found for account {}".format(data["username"])
            )
    except LoginError as error:
        raise InvalidAuth from error

    return locations


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LaCrosse View."""

    VERSION = 1
    data: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except NoLocations:
            errors["base"] = "no_locations"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            self.data = user_input
            return self.async_show_form(
                step_id="location",
                data_schema=vol.Schema(
                    {
                        vol.Required("location"): vol.In(
                            {
                                f"{location.id} {location.name}": location.name
                                for location in info
                            }
                        )
                    }
                ),
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_location(self, user_input: dict[str, Any]) -> FlowResult:
        """Handle the location step."""

        location_id = user_input["location"].split(" ")[0]
        location_name = user_input["location"].split(" ")[1]

        await self.async_set_unique_id(location_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=location_name,
            data={
                "id": location_id,
                "name": location_name,
                "username": self.data["username"],
                "password": self.data["password"],
            },
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class NoLocations(HomeAssistantError):
    """Error to indicate there are no locations."""
