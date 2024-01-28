"""Config flow for Ecovacs mqtt integration."""
from __future__ import annotations

import logging
from typing import Any, cast
from urllib.parse import urlparse

from aiohttp import ClientError
from deebot_client.authentication import Authenticator
from deebot_client.configuration import create_config
from deebot_client.exceptions import InvalidAuthenticationError
from deebot_client.util import md5
from deebot_client.util.continents import COUNTRIES_TO_CONTINENTS, get_continent
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_COUNTRY, CONF_MODE, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.helpers import aiohttp_client, selector
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.loader import async_get_issue_tracker

from .const import (
    CONF_CONTINENT,
    CONF_OVERRIDE_MQTT_URL,
    CONF_OVERRIDE_REST_URL,
    DOMAIN,
    InstanceMode,
)
from .util import get_client_device_id

_LOGGER = logging.getLogger(__name__)


def _validate_url(
    value: str,
    field_name: str,
    schema_list: set[str],
) -> dict[str, str]:
    """Validate an URL and return error dictionary."""
    if urlparse(value).scheme in schema_list:
        try:
            vol.Schema(vol.Url())(value)
            return {}
        except vol.Invalid:
            return {field_name: "invalid_url"}

    return {field_name: f"invalid_url_schema_{field_name}"}


async def _validate_input(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> dict[str, str]:
    """Validate user input."""
    errors: dict[str, str] = {}

    if rest_url := user_input.get(CONF_OVERRIDE_REST_URL):
        errors.update(
            _validate_url(rest_url, CONF_OVERRIDE_REST_URL, {"http", "https"})
        )
    if mqtt_url := user_input.get(CONF_OVERRIDE_MQTT_URL):
        errors.update(
            _validate_url(mqtt_url, CONF_OVERRIDE_MQTT_URL, {"mqtt", "mqtts"})
        )

    if errors:
        return errors

    deebot_config = create_config(
        aiohttp_client.async_get_clientsession(hass),
        device_id=get_client_device_id(),
        country=user_input[CONF_COUNTRY],
        override_rest_url=rest_url,
        override_mqtt_url=mqtt_url,
    )

    authenticator = Authenticator(
        deebot_config.rest,
        user_input[CONF_USERNAME],
        md5(user_input[CONF_PASSWORD]),
    )

    try:
        await authenticator.authenticate()
    except ClientError:
        _LOGGER.debug("Cannot connect", exc_info=True)
        errors["base"] = "cannot_connect"
    except InvalidAuthenticationError:
        errors["base"] = "invalid_auth"
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception during login")
        errors["base"] = "unknown"

    return errors


class EcovacsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ecovacs."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._mode: InstanceMode = InstanceMode.CLOUD

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        if not self.show_advanced_options:
            user_input = {CONF_MODE: InstanceMode.CLOUD}

        if user_input:
            self._mode = user_input[CONF_MODE]
            return await self.async_step_auth()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MODE, default=InstanceMode.CLOUD
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=list(InstanceMode),
                            translation_key="installation_mode",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            last_step=False,
        )

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the auth step."""
        errors = {}

        if user_input:
            self._async_abort_entries_match(
                {
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_OVERRIDE_REST_URL: user_input.get(CONF_OVERRIDE_REST_URL),
                }
            )

            errors = await _validate_input(self.hass, user_input)

            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )

        schema = {
            vol.Required(CONF_USERNAME): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required(CONF_COUNTRY): selector.CountrySelector(),
        }
        if self._mode == InstanceMode.SELF_HOSTED:
            schema.update(
                {
                    vol.Required(CONF_OVERRIDE_REST_URL): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                    ),
                    vol.Required(CONF_OVERRIDE_MQTT_URL): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                    ),
                }
            )

        if not user_input:
            user_input = {
                CONF_COUNTRY: self.hass.config.country,
            }

        return self.async_show_form(
            step_id="auth",
            data_schema=self.add_suggested_values_to_schema(
                data_schema=vol.Schema(schema), suggested_values=user_input
            ),
            errors=errors,
            last_step=True,
        )

    async def async_step_import(self, user_input: dict[str, Any]) -> FlowResult:
        """Import configuration from yaml."""

        def create_repair(
            error: str | None = None, placeholders: dict[str, Any] | None = None
        ) -> None:
            if placeholders is None:
                placeholders = {}
            if error:
                async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"deprecated_yaml_import_issue_{error}",
                    breaks_in_ha_version="2024.8.0",
                    is_fixable=False,
                    issue_domain=DOMAIN,
                    severity=IssueSeverity.WARNING,
                    translation_key=f"deprecated_yaml_import_issue_{error}",
                    translation_placeholders=placeholders
                    | {"url": "/config/integrations/dashboard/add?domain=ecovacs"},
                )
            else:
                async_create_issue(
                    self.hass,
                    HOMEASSISTANT_DOMAIN,
                    f"deprecated_yaml_{DOMAIN}",
                    breaks_in_ha_version="2024.8.0",
                    is_fixable=False,
                    issue_domain=DOMAIN,
                    severity=IssueSeverity.WARNING,
                    translation_key="deprecated_yaml",
                    translation_placeholders=placeholders
                    | {
                        "domain": DOMAIN,
                        "integration_title": "Ecovacs",
                    },
                )

        # We need to validate the imported country and continent
        # as the YAML configuration allows any string for them.
        # The config flow allows only valid alpha-2 country codes
        # through the CountrySelector.
        # The continent will be calculated with the function get_continent
        # from the country code and there is no need to specify the continent anymore.
        # As the YAML configuration includes the continent,
        # we check if both the entered continent and the calculated continent match.
        # If not we will inform the user about the mismatch.
        error = None
        placeholders = None
        if len(user_input[CONF_COUNTRY]) != 2:
            error = "invalid_country_length"
            placeholders = {"countries_url": "https://www.iso.org/obp/ui/#search/code/"}
        elif len(user_input[CONF_CONTINENT]) != 2:
            error = "invalid_continent_length"
            placeholders = {
                "continent_list": ",".join(
                    sorted(set(COUNTRIES_TO_CONTINENTS.values()))
                )
            }
        elif user_input[CONF_CONTINENT].lower() != (
            continent := get_continent(user_input[CONF_COUNTRY])
        ):
            error = "continent_not_match"
            placeholders = {
                "continent": continent,
                "github_issue_url": cast(
                    str, async_get_issue_tracker(self.hass, integration_domain=DOMAIN)
                ),
            }

        if error:
            create_repair(error, placeholders)
            return self.async_abort(reason=error)

        # Remove the continent from the user input as it is not needed anymore
        user_input.pop(CONF_CONTINENT)
        try:
            result = await self.async_step_auth(user_input)
        except AbortFlow as ex:
            if ex.reason == "already_configured":
                create_repair()
            raise ex

        if errors := result.get("errors"):
            error = errors["base"]
            create_repair(error)
            return self.async_abort(reason=error)

        create_repair()
        return result
