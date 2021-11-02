"""Config flow for HERE Travel Time integration."""
from __future__ import annotations

import logging
from typing import Any

from herepy import InvalidCredentialsError, RouteMode, RoutingApi
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.here_travel_time.sensor import (
    CONF_DESTINATION_ENTITY_ID,
    CONF_DESTINATION_LATITUDE,
    CONF_DESTINATION_LONGITUDE,
    CONF_ORIGIN_ENTITY_ID,
    CONF_ORIGIN_LATITUDE,
    CONF_ORIGIN_LONGITUDE,
)
from homeassistant.const import CONF_API_KEY, CONF_MODE, CONF_NAME, CONF_UNIT_SYSTEM
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    ARRIVAL_TIME,
    CONF_ARRIVAL,
    CONF_DEPARTURE,
    CONF_DESTINATION,
    CONF_ORIGIN,
    CONF_ROUTE_MODE,
    CONF_TIME,
    CONF_TIME_TYPE,
    CONF_TRAFFIC_MODE,
    DEFAULT_NAME,
    DEPARTURE_TIME,
    DOMAIN,
    ROUTE_MODE_FASTEST,
    ROUTE_MODES,
    TIME_TYPES,
    TRAFFIC_MODE_DISABLED,
    TRAFFIC_MODE_ENABLED,
    TRAFFIC_MODES,
    TRAVEL_MODE_CAR,
    TRAVEL_MODES,
    UNITS,
)

_LOGGER = logging.getLogger(__name__)


def is_dupe_import(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    user_input: dict[str, Any],
    options: dict[str, Any],
) -> bool:
    """Return whether imported config already exists."""
    # Check the main data keys
    if any(
        entry.data[key] != user_input[key]
        for key in (CONF_API_KEY, CONF_DESTINATION, CONF_ORIGIN, CONF_MODE, CONF_NAME)
    ):
        return False

    # We have to check for options that don't have defaults
    for key in (
        CONF_TRAFFIC_MODE,
        CONF_UNIT_SYSTEM,
        CONF_ROUTE_MODE,
        CONF_TIME_TYPE,
        CONF_TIME,
    ):
        if options.get(key) != entry.options.get(key):
            return False

    return True


def validate_input(data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect."""
    known_working_origin = [38.9, -77.04833]
    known_working_destination = [39.0, -77.1]
    RoutingApi(data[CONF_API_KEY]).public_transport_timetable(
        known_working_origin,
        known_working_destination,
        True,
        [
            RouteMode[ROUTE_MODE_FASTEST],
            RouteMode[TRAVEL_MODE_CAR],
            RouteMode[TRAFFIC_MODE_ENABLED],
        ],
        arrival=None,
        departure="now",
    )


def get_user_step_schema(data: dict[str, Any]) -> vol.Schema:
    """Get a populated schema or default."""
    name = DEFAULT_NAME if data.get(CONF_NAME) is None else data.get(CONF_NAME)
    mode = TRAVEL_MODE_CAR if data.get(CONF_MODE) is None else data.get(CONF_MODE)

    return vol.Schema(
        {
            vol.Optional(CONF_NAME, default=name): cv.string,
            vol.Required(CONF_API_KEY, default=data.get(CONF_API_KEY)): cv.string,
            vol.Required(
                CONF_DESTINATION, default=data.get(CONF_DESTINATION)
            ): cv.string,
            vol.Required(CONF_ORIGIN, default=data.get(CONF_ORIGIN)): cv.string,
            vol.Optional(CONF_MODE, default=mode): vol.In(TRAVEL_MODES),
        }
    )


class HERETravelTimeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HERE Travel Time."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HERETravelTimeOptionsFlow:
        """Get the options flow."""
        return HERETravelTimeOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        options = {}
        user_input = user_input or {}
        if user_input:
            if self.source == config_entries.SOURCE_IMPORT:
                if user_input.get(CONF_ORIGIN_LATITUDE) is not None:
                    user_input[
                        CONF_ORIGIN
                    ] = f"{user_input.pop(CONF_ORIGIN_LATITUDE)},{user_input.pop(CONF_ORIGIN_LONGITUDE)}"
                else:
                    user_input[CONF_ORIGIN] = user_input.pop(CONF_ORIGIN_ENTITY_ID)

                if user_input.get(CONF_DESTINATION_LATITUDE) is not None:
                    user_input[
                        CONF_DESTINATION
                    ] = f"{user_input.pop(CONF_DESTINATION_LATITUDE)},{user_input.pop(CONF_DESTINATION_LONGITUDE)}"
                else:
                    user_input[CONF_DESTINATION] = user_input.pop(
                        CONF_DESTINATION_ENTITY_ID
                    )

                options[CONF_TRAFFIC_MODE] = (
                    TRAFFIC_MODE_ENABLED
                    if user_input.pop(CONF_TRAFFIC_MODE, False)
                    else TRAFFIC_MODE_DISABLED
                )
                options[CONF_ROUTE_MODE] = user_input.pop(CONF_ROUTE_MODE)
                options[CONF_UNIT_SYSTEM] = user_input.pop(
                    CONF_UNIT_SYSTEM, self.hass.config.units.name
                )
                options[CONF_TIME_TYPE] = (
                    ARRIVAL_TIME if CONF_ARRIVAL in user_input else DEPARTURE_TIME
                )
                if (arrival_time := user_input.pop(CONF_ARRIVAL, None)) is not None:
                    options[CONF_TIME] = arrival_time
                if (departure_time := user_input.pop(CONF_DEPARTURE, None)) is not None:
                    options[CONF_TIME] = departure_time

                # We need to prevent duplicate imports
                if any(
                    is_dupe_import(self.hass, entry, user_input, options)
                    for entry in self.hass.config_entries.async_entries(DOMAIN)
                    if entry.source == config_entries.SOURCE_IMPORT
                ):
                    return self.async_abort(reason="already_configured")
            try:
                await self.hass.async_add_executor_job(validate_input, user_input)
            except InvalidCredentialsError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input["name"], data=user_input, options=options
                )

        return self.async_show_form(
            step_id="user", data_schema=get_user_step_schema(user_input), errors=errors
        )

    async_step_import = async_step_user


class HERETravelTimeOptionsFlow(config_entries.OptionsFlow):
    """Handle HERE Travel Time options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize HERE Travel Time options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the HERE Travel Time options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_TRAFFIC_MODE,
                default=self.config_entry.options.get(
                    CONF_TRAFFIC_MODE, TRAFFIC_MODE_ENABLED
                ),
            ): vol.In(TRAFFIC_MODES),
            vol.Optional(
                CONF_ROUTE_MODE,
                default=self.config_entry.options.get(
                    CONF_ROUTE_MODE, ROUTE_MODE_FASTEST
                ),
            ): vol.In(ROUTE_MODES),
            vol.Optional(CONF_TIME_TYPE, default=DEPARTURE_TIME): vol.In(TIME_TYPES),
            vol.Optional(CONF_TIME, default=""): cv.string,
            vol.Optional(
                CONF_UNIT_SYSTEM,
                default=self.config_entry.options.get(
                    CONF_UNIT_SYSTEM, self.hass.config.units.name
                ),
            ): vol.In(UNITS),
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
