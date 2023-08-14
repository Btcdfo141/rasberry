"""Config flow for Linear Garage Door integration."""
from __future__ import annotations

import logging
from typing import Any
import uuid

from linear_garage_door import Linear
from linear_garage_door.errors import InvalidDeviceIDError, InvalidLoginError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = {
    vol.Required("email"): str,
    vol.Required("password"): str,
}


async def validate_input(
    hass: HomeAssistant,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    hub = Linear()

    device_id = data.get("device_id", str(uuid.uuid4()))

    try:
        await hub.login(
            data["email"],
            data["password"],
            device_id=device_id,
            client_session=async_get_clientsession(hass),
        )
    except InvalidLoginError as err:
        raise InvalidAuth from err
    except InvalidDeviceIDError as err:
        raise InvalidDeviceID from err

    sites = await hub.get_sites()

    info = {
        "email": data["email"],
        "password": data["password"],
        "sites": sites,
        "device_id": device_id,
    }

    await hub.close()

    # Return info that you want to store in the config entry.
    return info


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Linear Garage Door."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data: dict[str, str | list[dict[str, str]]] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            data_schema = STEP_USER_DATA_SCHEMA

            if self.show_advanced_options:
                data_schema["device_id"] = str

            data_schema = vol.Schema(data_schema)

            return self.async_show_form(step_id="user", data_schema=data_schema)

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except InvalidDeviceID:
            errors["base"] = "invalid_device_id"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            self.data = info
            return await self.async_step_site()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_site(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the site step."""

        if isinstance(self.data["sites"], list):
            sites: list[dict[str, str]] = list(self.data["sites"])

        if not user_input:
            return self.async_show_form(
                step_id="site",
                data_schema=vol.Schema(
                    {
                        vol.Required("site"): vol.In(
                            {site["id"]: site["name"] for site in sites}
                        )
                    }
                ),
            )

        site_id = user_input["site"]

        site_name = next(site["name"] for site in sites if site["id"] == site_id)

        await self.async_set_unique_id(site_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=site_name,
            data={
                "site_id": site_id,
                "email": self.data["email"],
                "password": self.data["password"],
                "device_id": self.data["device_id"],
            },
        )


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidDeviceID(HomeAssistantError):
    """Error to indicate there is invalid device ID."""
