"""Config flow for Flux integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from voluptuous.schema_builder import UNDEFINED

from homeassistant import config_entries
from homeassistant.components.light import ATTR_TRANSITION
from homeassistant.config_entries import (
    ConfigEntry,
    OptionsFlow,
    OptionsFlowWithConfigEntry,
)
from homeassistant.const import (
    CONF_BRIGHTNESS,
    CONF_LIGHTS,
    CONF_MODE,
    CONF_NAME,
    Platform,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    ColorTempSelector,
    ColorTempSelectorConfig,
    DurationSelector,
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TimeSelector,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.color import (
    color_temperature_kelvin_to_mired,
    color_temperature_mired_to_kelvin,
)

from .const import (
    CONF_ADJUST_BRIGHTNESS,
    CONF_INTERVAL,
    CONF_START_CT,
    CONF_START_TIME,
    CONF_STOP_CT,
    CONF_STOP_TIME,
    CONF_SUNSET_CT,
    DEFAULT_INTERVAL_DURATION,
    DEFAULT_MODE,
    DEFAULT_NAME,
    DEFAULT_START_COLOR_TEMP_KELVIN,
    DEFAULT_STOP_COLOR_TEMP_KELVIN,
    DEFAULT_SUNSET_COLOR_TEMP_KELVIN,
    DEFAULT_TRANSITION_DURATION,
    DOMAIN,
    MODE_MIRED,
    MODE_RGB,
    MODE_XY,
)
from .switch import CONF_DISABLE_BRIGHTNESS_ADJUST

_LOGGER = logging.getLogger(__name__)

MINIMAL_FLUX_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_LIGHTS): EntitySelector(
            EntitySelectorConfig(domain=Platform.LIGHT, multiple=True)
        ),
    }
)

allowed_colortemp_range = ColorTempSelectorConfig(
    {
        "min_mireds": color_temperature_kelvin_to_mired(40000),
        "max_mireds": color_temperature_kelvin_to_mired(1000),
    }
)


def default_settings():
    """Return object with the default settings for the Flux integration."""
    settings_dict = {}
    settings_dict[CONF_START_CT] = DEFAULT_START_COLOR_TEMP_KELVIN
    settings_dict[CONF_SUNSET_CT] = DEFAULT_SUNSET_COLOR_TEMP_KELVIN
    settings_dict[CONF_STOP_CT] = DEFAULT_STOP_COLOR_TEMP_KELVIN
    settings_dict[CONF_ADJUST_BRIGHTNESS] = True
    settings_dict[CONF_MODE] = DEFAULT_MODE
    settings_dict[CONF_INTERVAL] = DEFAULT_INTERVAL_DURATION
    settings_dict[ATTR_TRANSITION] = DEFAULT_TRANSITION_DURATION
    return settings_dict


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Flux."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for the Flux component."""
        return FluxOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        if user_input is not None:
            user_input.update(default_settings())
            return self.async_create_entry(
                title=user_input[CONF_NAME], data={}, options=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=MINIMAL_FLUX_SCHEMA,
        )

    async def async_step_import(self, yaml_config: ConfigType) -> FlowResult:
        """Handle import from configuration.yaml."""
        # start with the same default settings as in the UI
        entry_options = default_settings()

        # remove the old two very similar options
        brightness = yaml_config.get(CONF_BRIGHTNESS, False)
        disable_brightness_adjust = yaml_config.get(
            CONF_DISABLE_BRIGHTNESS_ADJUST, False
        )

        # combine them into the "new" option
        if brightness or disable_brightness_adjust:
            entry_options[CONF_ADJUST_BRIGHTNESS] = False

        if CONF_INTERVAL in yaml_config:
            entry_options[CONF_INTERVAL] = {"seconds": yaml_config[CONF_INTERVAL]}
        if ATTR_TRANSITION in yaml_config:
            entry_options[ATTR_TRANSITION] = {"seconds": yaml_config[ATTR_TRANSITION]}

        if CONF_START_TIME in yaml_config:
            entry_options[CONF_START_TIME] = str(yaml_config[CONF_START_TIME])

        if CONF_STOP_TIME in yaml_config:
            entry_options[CONF_STOP_TIME] = str(yaml_config[CONF_STOP_TIME])

        # apply the rest of the remaining options
        entry_options[CONF_LIGHTS] = yaml_config[CONF_LIGHTS]
        if CONF_MODE in yaml_config:
            entry_options[CONF_MODE] = yaml_config[CONF_MODE]
        if CONF_START_CT in yaml_config:
            entry_options[CONF_START_CT] = yaml_config[CONF_START_CT]
        if CONF_SUNSET_CT in yaml_config:
            entry_options[CONF_SUNSET_CT] = yaml_config[CONF_SUNSET_CT]
        if CONF_STOP_CT in yaml_config:
            entry_options[CONF_STOP_CT] = yaml_config[CONF_STOP_CT]
        if CONF_NAME in yaml_config:
            entry_options[CONF_NAME] = yaml_config[CONF_NAME]

        self._async_abort_entries_match(entry_options)

        return self.async_create_entry(
            title=entry_options.get(CONF_NAME, DEFAULT_NAME),
            data={},
            options=entry_options,
        )


class FluxOptionsFlow(OptionsFlowWithConfigEntry):
    """Handle flux options."""

    def reset_values_to_default(self, user_input):
        """Hacky method to reset saved values and use the default again."""
        time_that_signals_to_reset_to_defeault = "13:37:00"
        values_that_signal_to_reset_to_default = [
            time_that_signals_to_reset_to_defeault,
        ]

        return {
            key: value
            for key, value in user_input.items()
            if value not in values_that_signal_to_reset_to_default
        }

    def convert_mired_stuff_to_kelvin(self, user_input):
        """Convert between mireds and kelvins because I can't find the kelvin option for ColorTempSelector."""
        user_input[CONF_START_CT] = color_temperature_mired_to_kelvin(
            user_input[CONF_START_CT]
        )
        user_input[CONF_SUNSET_CT] = color_temperature_mired_to_kelvin(
            user_input[CONF_SUNSET_CT]
        )
        user_input[CONF_STOP_CT] = color_temperature_mired_to_kelvin(
            user_input[CONF_STOP_CT]
        )

        return user_input

    def remove_undefined(self, user_input):
        """Remove keys with values that are UNDEFINED."""
        return {key: value for key, value in user_input.items() if value != UNDEFINED}

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Configure the options."""
        if user_input is not None:
            user_input = self.reset_values_to_default(user_input)
            user_input = self.convert_mired_stuff_to_kelvin(user_input)
            user_input = self.remove_undefined(user_input)

            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        settings = self._config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=settings.get(CONF_NAME)): str,
                    vol.Required(
                        CONF_LIGHTS, default=settings.get(CONF_LIGHTS)
                    ): EntitySelector(
                        EntitySelectorConfig(domain=Platform.LIGHT, multiple=True)
                    ),
                    # times
                    vol.Optional(
                        CONF_START_TIME,
                        default=settings.get(CONF_START_TIME, UNDEFINED),
                    ): TimeSelector(),
                    vol.Optional(
                        CONF_STOP_TIME, default=settings.get(CONF_STOP_TIME, UNDEFINED)
                    ): TimeSelector(),
                    # colors
                    vol.Optional(
                        CONF_START_CT,
                        default=color_temperature_kelvin_to_mired(
                            float(settings.get(CONF_START_CT))  # type: ignore[arg-type]
                        ),
                    ): ColorTempSelector(allowed_colortemp_range),
                    vol.Optional(
                        CONF_SUNSET_CT,
                        default=color_temperature_kelvin_to_mired(
                            float(settings.get(CONF_SUNSET_CT))  # type: ignore[arg-type]
                        ),
                    ): ColorTempSelector(allowed_colortemp_range),
                    vol.Optional(
                        CONF_STOP_CT,
                        default=color_temperature_kelvin_to_mired(
                            float(settings.get(CONF_STOP_CT))  # type: ignore[arg-type]
                        ),
                    ): ColorTempSelector(allowed_colortemp_range),
                    # adjust_brightness
                    vol.Optional(
                        CONF_ADJUST_BRIGHTNESS,
                        default=settings.get(CONF_ADJUST_BRIGHTNESS),
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_MODE, default=settings.get(CONF_MODE)
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=MODE_XY, label=MODE_XY),
                                SelectOptionDict(value=MODE_MIRED, label=MODE_MIRED),
                                SelectOptionDict(value=MODE_RGB, label=MODE_RGB),
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    # update settings
                    vol.Optional(
                        ATTR_TRANSITION, default=settings.get(ATTR_TRANSITION)
                    ): DurationSelector(),
                    vol.Optional(
                        CONF_INTERVAL, default=settings.get(CONF_INTERVAL)
                    ): DurationSelector(),
                }
            ),
        )
