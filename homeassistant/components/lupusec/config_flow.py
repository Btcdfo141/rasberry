""""Config flow for Lupusec integration."""

import ipaddress
import logging
import socket
from typing import Any

import lupupy
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_NAME): str,
    }
)


class LupusecConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Lupusec config flow."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            name = user_input.get(CONF_NAME)

            try:
                errors = await validate_user_input(
                    self.hass, host, username, password, name
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if not errors:
                return self.async_create_entry(
                    title=host,
                    data={
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_NAME: name,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_import(self, user_input: dict[str, Any]) -> FlowResult:
        """Import the yaml config."""
        self._async_abort_entries_match(user_input)
        host = user_input[CONF_HOST]
        username = user_input[CONF_USERNAME]
        password = user_input[CONF_PASSWORD]
        name = user_input.get(CONF_NAME)
        try:
            await validate_user_input(self.hass, host, username, password, name)
        except CannotConnect:
            return self.async_abort(reason="cannot_connect")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            return self.async_abort(reason="unknown")

        return self.async_create_entry(title=host, data=user_input)


async def validate_user_input(hass: HomeAssistant, host, username, password, name):
    """Validate the provided configuration."""
    errors = {}

    if not is_valid_host(host):
        errors[CONF_HOST] = "invalid_host"

    await test_host_connection(hass, host, username, password)

    return errors


def is_valid_host(host):
    """Check if the provided value is a valid DNS name or IP address."""

    if not isinstance(host, (str, bytes)):
        return False
    try:
        # Try to parse the host as an IP address
        ipaddress.ip_address(host)
        return True
    except ValueError:
        # If parsing as an IP address fails, try as a DNS name
        try:
            ipaddress.ip_address(socket.gethostbyname(host))
            return True
        except (socket.herror, ValueError, socket.gaierror):
            return False


async def test_host_connection(hass, host, username, password):
    """Test if the host is reachable and is actually a Lupusec device."""
    try:
        await hass.async_add_executor_job(lupupy.Lupusec, username, password, host)
    except lupupy.LupusecException:
        _LOGGER.error("Failed to connect to Lupusec device at %s", host)
        raise CannotConnect
    except Exception:  # pylint: disable=broad-except
        _LOGGER.error("Failed to connect to Lupusec device at %s", host)
        raise CannotConnect


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
