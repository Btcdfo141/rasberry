"""Collection of helper methods.

All containing methods are legacy helpers that should not be used by new
components. Instead call the service directly.
"""
from homeassistant.components.remote import (
    ATTR_ACTIVITY, ATTR_COMMAND, ATTR_DELAY_SECS, ATTR_DEVICE,
    ATTR_NUM_REPEATS, DOMAIN, SERVICE_SEND_COMMAND)
from homeassistant.const import (
    ATTR_ENTITY_ID, SERVICE_TOGGLE, SERVICE_TURN_OFF, SERVICE_TURN_ON)
from homeassistant.loader import bind_hass


@bind_hass
def turn_on(hass, activity=None, entity_id=None):
    """Turn all or specified remote on."""
    data = {
        key: value for key, value in [
            (ATTR_ACTIVITY, activity),
            (ATTR_ENTITY_ID, entity_id),
        ] if value is not None}
    hass.services.call(DOMAIN, SERVICE_TURN_ON, data)


@bind_hass
def turn_off(hass, activity=None, entity_id=None):
    """Turn all or specified remote off."""
    data = {}
    if activity:
        data[ATTR_ACTIVITY] = activity

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_TURN_OFF, data)


@bind_hass
def toggle(hass, activity=None, entity_id=None):
    """Toggle all or specified remote."""
    data = {}
    if activity:
        data[ATTR_ACTIVITY] = activity

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_TOGGLE, data)


@bind_hass
def send_command(hass, command, entity_id=None, device=None,
                 num_repeats=None, delay_secs=None):
    """Send a command to a device."""
    data = {ATTR_COMMAND: command}
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    if device:
        data[ATTR_DEVICE] = device

    if num_repeats:
        data[ATTR_NUM_REPEATS] = num_repeats

    if delay_secs:
        data[ATTR_DELAY_SECS] = delay_secs

    hass.services.call(DOMAIN, SERVICE_SEND_COMMAND, data)
