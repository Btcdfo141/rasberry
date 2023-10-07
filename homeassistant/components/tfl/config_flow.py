"""Config flow for Transport for London integration."""
from __future__ import annotations

from copy import deepcopy
import logging
from typing import Any
from urllib.error import HTTPError, URLError

from tflwrapper import stopPoint
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .config_helper import config_from_entry
from .const import (
    CONF_API_APP_KEY,
    CONF_STOP_POINT,
    CONF_STOP_POINT_ADD_ANOTHER,
    CONF_STOP_POINTS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_API_APP_KEY, default=""): cv.string,
    }
)
STEP_STOP_POINT_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STOP_POINT): cv.string,
        vol.Optional(CONF_STOP_POINT_ADD_ANOTHER): cv.boolean,
    }
)


async def validate_app_key(hass: HomeAssistant, app_key: str) -> None:
    """Validate the user input for app_key."""

    _LOGGER.debug("Validating app_key")
    stop_point_api = stopPoint(app_key)
    # Make a random, cheap, call to the API to validate the app_key
    try:
        categories = await hass.async_add_executor_job(stop_point_api.getCategories)
        _LOGGER.debug("Validating app_key, got categories=%s", categories)
    except HTTPError as exception:
        # TfL's API returns a 429 if you pass an invalid app_key, but we also check
        # for other reasonable error codes in case their behaviour changes
        error_code = exception.getcode()
        if error_code in (429, 401, 403):
            raise InvalidAuth from exception

        raise
    except URLError as exception:
        raise CannotConnect from exception


async def validate_stop_point(
    hass: HomeAssistant, app_key: str, stop_point: str
) -> None:
    """Validate the user input for stop point."""

    _LOGGER.debug("Validating stop_point=%s", stop_point)

    try:
        stop_point_api = stopPoint(app_key)
        _LOGGER.debug("Validating stop_point=%s", stop_point)
        arrivals = await hass.async_add_executor_job(
            stop_point_api.getStationArrivals, stop_point
        )
        _LOGGER.debug("Got for stop_point=%s, arrivals=%s", stop_point, arrivals)
    except HTTPError as exception:
        # TfL's API returns a 429 if you pass an invalid app_key, but we also check
        # for other reasonable error codes in case their behaviour changes
        error_code = exception.getcode()
        if error_code in (429, 401, 403):
            raise InvalidAuth from exception

        if error_code == 404:
            raise ValueError from exception

        raise
    except URLError as exception:
        raise CannotConnect from exception


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Transport for London."""

    VERSION = 1
    data: dict[str, Any] = {}

    # def __init__(self) -> None:
    #     """Initialise any data needed for the config flow."""
    #     self.data = dict[str, Any]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_app_key(self.hass, user_input[CONF_API_APP_KEY])
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Input is valid, set data
                self.data = user_input
                self.data[CONF_STOP_POINTS] = []
                return await self.async_step_stop_point()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_stop_point(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the stop point step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                app_key = self.data[CONF_API_APP_KEY]
                await validate_stop_point(
                    self.hass,
                    app_key,
                    user_input[CONF_STOP_POINT],
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ValueError:
                errors["base"] = "invalid_stop_point"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # User input is valid, save the stop point
                self.data[CONF_STOP_POINTS].append(user_input[CONF_STOP_POINT])
                # If user ticked the box show this form again so they can add an
                # additional stop point.
                if user_input.get(CONF_STOP_POINT_ADD_ANOTHER, False):
                    return await self.async_step_stop_point()

                # return await self.async_step_stop_points()
                return self.async_create_entry(
                    title="Transport for London", data=self.data
                )

        return self.async_show_form(
            step_id="stop_point",
            data_schema=STEP_STOP_POINT_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options for the TfL component."""
        errors: dict[str, str] = {}

        config = config_from_entry(self.config_entry)
        api_key = deepcopy(config[CONF_API_APP_KEY])
        all_stops = deepcopy(config[CONF_STOP_POINTS])

        if user_input is not None:
            updated_stops = user_input["stops"]
            if (
                CONF_STOP_POINT in user_input
                and user_input[CONF_STOP_POINT] is not None
            ):
                updated_stops.append(user_input[CONF_STOP_POINT])

            data: dict[str, Any] = {}
            data[CONF_API_APP_KEY] = user_input[CONF_API_APP_KEY]
            data[CONF_STOP_POINTS] = updated_stops

            if not errors:
                # Value of data will be set on the options property of our config_entry
                # instance.
                return self.async_create_entry(
                    title="Transport for London",
                    data=data,
                )

        options_schema = vol.Schema(
            {
                vol.Optional(CONF_API_APP_KEY, default=api_key): cv.string,
                vol.Optional("stops", default=list(all_stops)): cv.multi_select(
                    all_stops
                ),
                vol.Optional(CONF_STOP_POINT): cv.string,
                # vol.Optional(CONF_NAME): cv.string,
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
