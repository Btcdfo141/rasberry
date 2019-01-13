"""
Support for Locative.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/locative/
"""
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import \
    DOMAIN as DEVICE_TRACKER_DOMAIN
from homeassistant.const import HTTP_UNPROCESSABLE_ENTITY, ATTR_LATITUDE, \
    ATTR_LONGITUDE, STATE_NOT_HOME, CONF_WEBHOOK_ID, ATTR_ID
from homeassistant.helpers import config_entry_flow
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'locative'
DEPENDENCIES = ['webhook']

TRACKER_UPDATE = '{}_tracker_update'.format(DOMAIN)


ATTR_DEVICE_ID = 'device'
ATTR_TRIGGER = 'trigger'

WEBHOOK_SCHEMA = vol.Schema({
    vol.Required(ATTR_LATITUDE): cv.latitude,
    vol.Required(ATTR_LONGITUDE): cv.longitude,
    vol.Required(ATTR_DEVICE_ID): cv.string,
    vol.Required(ATTR_TRIGGER): cv.string,
    vol.Optional(ATTR_ID): cv.string,
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, hass_config):
    """Set up the Locative component."""
    hass.async_create_task(
        async_load_platform(hass, 'device_tracker', DOMAIN, {}, hass_config)
    )
    return True


async def handle_webhook(hass, webhook_id, request):
    """Handle incoming webhook from Locative."""
    try:
        data = WEBHOOK_SCHEMA(dict(await request.post()))
    except vol.MultipleInvalid as e:
        return e.error_message, HTTP_UNPROCESSABLE_ENTITY

    if ATTR_ID not in data and data[ATTR_TRIGGER] != 'test':
        _LOGGER.error('Location id not specified.')
        return ('Location id not specified.',
                HTTP_UNPROCESSABLE_ENTITY)

    device = data[ATTR_DEVICE_ID].replace('-', '')
    location_name = data.get(ATTR_ID, data[ATTR_TRIGGER]).lower()
    direction = data[ATTR_TRIGGER]
    gps_location = (data[ATTR_LATITUDE], data[ATTR_LONGITUDE])

    if direction == 'enter':
        async_dispatcher_send(
            hass,
            TRACKER_UPDATE,
            device,
            gps_location,
            location_name
        )
        return 'Setting location to {}'.format(location_name)

    if direction == 'exit':
        current_state = hass.states.get(
            '{}.{}'.format(DEVICE_TRACKER_DOMAIN, device))

        if current_state is None or current_state.state == location_name:
            location_name = STATE_NOT_HOME
            async_dispatcher_send(
                hass,
                TRACKER_UPDATE,
                device,
                gps_location,
                location_name
            )
            return 'Setting location to not home'

        # Ignore the message if it is telling us to exit a zone that we
        # aren't currently in. This occurs when a zone is entered
        # before the previous zone was exited. The enter message will
        # be sent first, then the exit message will be sent second.
        return 'Ignoring exit from {} (already in {})'.format(
            location_name, current_state)

    if direction == 'test':
        # In the app, a test message can be sent. Just return something to
        # the user to let them know that it works.
        return 'Received test message.'

    _LOGGER.error('Received unidentified message from Locative: %s',
                  direction)
    return ('Received unidentified message: {}'.format(direction),
            HTTP_UNPROCESSABLE_ENTITY)


async def async_setup_entry(hass, entry):
    """Configure based on config entry."""
    hass.components.webhook.async_register(
        DOMAIN, 'Locative', entry.data[CONF_WEBHOOK_ID], handle_webhook)
    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    hass.components.webhook.async_unregister(entry.data[CONF_WEBHOOK_ID])
    return True

config_entry_flow.register_webhook_flow(
    DOMAIN,
    'Locative Webhook',
    {
        'docs_url': 'https://www.home-assistant.io/components/locative/'
    }
)
