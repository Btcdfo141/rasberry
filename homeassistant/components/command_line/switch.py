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
    CONF_SWITCHES,
    CONF_UNIQUE_ID,
    CONF_VALUE_TEMPLATE,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.reload import setup_reload_service
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import CommandData
from .const import CONF_COMMAND_TIMEOUT, DEFAULT_TIMEOUT, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

SWITCH_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_COMMAND_OFF, default="true"): cv.template,
        vol.Optional(CONF_COMMAND_ON, default="true"): cv.template,
        vol.Optional(CONF_COMMAND_STATE, default=None): vol.Any(cv.template, None),
        vol.Optional(CONF_FRIENDLY_NAME): cv.string,
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
        vol.Optional(CONF_ICON_TEMPLATE): cv.template,
        vol.Optional(CONF_COMMAND_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_SWITCHES): cv.schema_with_slug_keys(SWITCH_SCHEMA)}
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Find and return switches controlled by shell commands."""

    setup_reload_service(hass, DOMAIN, PLATFORMS)

    devices = config.get(CONF_SWITCHES, {})
    switches = []

    for object_id, device_config in devices.items():
        value_template = device_config.get(CONF_VALUE_TEMPLATE)

        if value_template is not None:
            value_template.hass = hass

        icon_template = device_config.get(CONF_ICON_TEMPLATE)
        if icon_template is not None:
            icon_template.hass = hass

        switches.append(
            CommandSwitch(
                hass,
                object_id,
                device_config.get(CONF_FRIENDLY_NAME, object_id),
                device_config[CONF_COMMAND_ON],
                device_config[CONF_COMMAND_OFF],
                device_config.get(CONF_COMMAND_STATE),
                icon_template,
                value_template,
                device_config[CONF_COMMAND_TIMEOUT],
                device_config.get(CONF_UNIQUE_ID),
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
        self.entity_id = ENTITY_ID_FORMAT.format(object_id)
        self._name = friendly_name
        self._state = False
        self._command_on = (
            CommandData(hass, command_on, timeout) if command_on else command_on
        )
        self._command_off = (
            CommandData(hass, command_off, timeout) if command_off else command_off
        )
        self._command_state = (
            CommandData(hass, command_state, timeout)
            if command_state
            else command_state
        )
        self._icon_template = icon_template
        self._value_template = value_template
        self._timeout = timeout
        self._attr_unique_id = unique_id

    @classmethod
    def _switch(cls, command):
        """Execute the actual commands."""
        success = command.update(False) == 0

        if not success:
            _LOGGER.error("Command failed: %s", command)

        return success

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
            return self._command_state.update(True)
        return self._command_state.update(False) == 0

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
