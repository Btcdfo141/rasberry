"""Support for custom shell commands to turn a switch on/off."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    SwitchEntity,
)
from homeassistant.const import (
    CONF_COMMAND_OFF,
    CONF_COMMAND_ON,
    CONF_COMMAND_STATE,
    CONF_FRIENDLY_NAME,
    CONF_ICON_TEMPLATE,
    CONF_NAME,
    CONF_SWITCHES,
    CONF_UNIQUE_ID,
    CONF_VALUE_TEMPLATE,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import call_shell_with_timeout, check_output_or_log
from .const import CONF_COMMAND_TIMEOUT, DEFAULT_TIMEOUT

_LOGGER = logging.getLogger(__name__)

SWITCH_LEGACY_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_COMMAND_OFF, default="true"): cv.string,
        vol.Optional(CONF_COMMAND_ON, default="true"): cv.string,
        vol.Optional(CONF_COMMAND_STATE): cv.string,
        vol.Optional(CONF_FRIENDLY_NAME): cv.string,
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
        vol.Optional(CONF_ICON_TEMPLATE): cv.template,
        vol.Optional(CONF_COMMAND_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

SWITCH_SCHEMA = SWITCH_LEGACY_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_SWITCHES): cv.schema_with_slug_keys(SWITCH_LEGACY_SCHEMA)}
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Find and return switches controlled by shell commands."""
    if discovery_info is None:
        entities = [
            dict(entity, **{CONF_NAME: entity_name})
            for (entity_name, entity) in config[CONF_SWITCHES].items()
        ]
    else:
        entities = discovery_info["entities"]

    switches = []

    for entity in entities:
        value_template = entity.get(CONF_VALUE_TEMPLATE)
        if value_template is not None:
            value_template.hass = hass

        icon_template = entity.get(CONF_ICON_TEMPLATE)
        if icon_template is not None:
            icon_template.hass = hass

        switches.append(
            CommandSwitch(
                hass,
                entity.get(CONF_NAME),
                entity.get(CONF_FRIENDLY_NAME, entity.get(CONF_NAME)),
                entity[CONF_COMMAND_ON],
                entity[CONF_COMMAND_OFF],
                entity.get(CONF_COMMAND_STATE),
                icon_template,
                value_template,
                entity[CONF_COMMAND_TIMEOUT],
                entity.get(CONF_UNIQUE_ID),
            )
        )

    if not switches:
        _LOGGER.error("No switches added")
        return

    add_entities(switches)


class CommandSwitch(SwitchEntity):
    """Representation a switch that can be toggled using shell commands."""

    def __init__(
        self,
        hass,
        object_id,
        friendly_name,
        command_on,
        command_off,
        command_state,
        icon_template,
        value_template,
        timeout,
        unique_id,
    ):
        """Initialize the switch."""
        self._hass = hass
        if object_id:
            self.entity_id = async_generate_entity_id(
                ENTITY_ID_FORMAT, object_id, hass=hass
            )
        self._name = friendly_name
        self._state = False
        self._command_on = command_on
        self._command_off = command_off
        self._command_state = command_state
        self._icon_template = icon_template
        self._value_template = value_template
        self._timeout = timeout
        self._attr_unique_id = unique_id

    def _switch(self, command):
        """Execute the actual commands."""
        _LOGGER.info("Running command: %s", command)

        success = call_shell_with_timeout(command, self._timeout) == 0

        if not success:
            _LOGGER.error("Command failed: %s", command)

        return success

    def _query_state_value(self, command):
        """Execute state command for return value."""
        _LOGGER.info("Running state value command: %s", command)
        return check_output_or_log(command, self._timeout)

    def _query_state_code(self, command):
        """Execute state command for return code."""
        _LOGGER.info("Running state code command: %s", command)
        return (
            call_shell_with_timeout(command, self._timeout, log_return_code=False) == 0
        )

    @property
    def should_poll(self):
        """Only poll if we have state command."""
        return self._command_state is not None

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def assumed_state(self):
        """Return true if we do optimistic updates."""
        return self._command_state is None

    def _query_state(self):
        """Query for state."""
        if self._value_template:
            return self._query_state_value(self._command_state)
        return self._query_state_code(self._command_state)

    def update(self):
        """Update device state."""
        if self._command_state:
            payload = str(self._query_state())
            if self._icon_template:
                self._attr_icon = self._icon_template.render_with_possible_json_value(
                    payload
                )
            if self._value_template:
                payload = self._value_template.render_with_possible_json_value(payload)
            self._state = payload.lower() == "true"

    def turn_on(self, **kwargs):
        """Turn the device on."""
        if self._switch(self._command_on) and not self._command_state:
            self._state = True
            self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        if self._switch(self._command_off) and not self._command_state:
            self._state = False
            self.schedule_update_ha_state()
