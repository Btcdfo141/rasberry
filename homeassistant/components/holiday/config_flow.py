"""Config flow for Holiday integration."""
from __future__ import annotations

from typing import Any

from babel import Locale, UnknownLocaleError
from holidays import country_holidays, list_supported_countries
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_COUNTRY
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.selector import (
    CountrySelector,
    CountrySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_CATEGORIES, CONF_PROVINCE, DOMAIN

SUPPORTED_COUNTRIES = list_supported_countries(include_aliases=False)


class HolidayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Holiday."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            self.data = user_input

            selected_country = user_input[CONF_COUNTRY]

            if SUPPORTED_COUNTRIES[selected_country]:
                return await self.async_step_province()

            self._async_abort_entries_match({CONF_COUNTRY: user_input[CONF_COUNTRY]})

            try:
                locale = Locale.parse(self.hass.config.language, sep="-")
            except UnknownLocaleError:
                # Default to (US) English if language not recognized by babel
                # Mainly an issue with English flavors such as "en-GB"
                locale = Locale("en")
            title = locale.territories[selected_country]
            return self.async_create_entry(title=title, data=user_input)

        user_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_COUNTRY, default=self.hass.config.country
                ): CountrySelector(
                    CountrySelectorConfig(
                        countries=list(SUPPORTED_COUNTRIES),
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=user_schema)

    async def async_step_province(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the province step."""
        if user_input is not None:
            combined_input: dict[str, Any] = {**self.data, **user_input}

            country = combined_input[CONF_COUNTRY]
            province = combined_input.get(CONF_PROVINCE)

            self._async_abort_entries_match(
                {
                    CONF_COUNTRY: country,
                    CONF_PROVINCE: province,
                }
            )

            try:
                locale = Locale.parse(self.hass.config.language, sep="-")
            except UnknownLocaleError:
                # Default to (US) English if language not recognized by babel
                # Mainly an issue with English flavors such as "en-GB"
                locale = Locale("en")
            province_str = f", {province}" if province else ""
            name = f"{locale.territories[country]}{province_str}"

            return self.async_create_entry(title=name, data=combined_input)

        province_schema = vol.Schema(
            {
                vol.Optional(CONF_PROVINCE): SelectSelector(
                    SelectSelectorConfig(
                        options=SUPPORTED_COUNTRIES[self.data[CONF_COUNTRY]],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="province", data_schema=province_schema)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Holiday."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            changed = self.hass.config_entries.async_update_entry(
                self.config_entry,
                options=user_input,
            )
            if changed:
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data=user_input)

        obj_holidays = country_holidays(
            self.config_entry.data[CONF_COUNTRY],
            subdiv=self.config_entry.data.get(CONF_PROVINCE),
        )
        supported_categories = sorted(obj_holidays.supported_categories)

        configured_categories: list[str] = self.config_entry.options.get(
            CONF_CATEGORIES, ["public"]
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CATEGORIES, default=configured_categories
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=supported_categories,
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                            translation_key=CONF_CATEGORIES,
                        )
                    ),
                }
            ),
        )
