"""
Support for the Geofency platform.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.geofency/
"""
import asyncio
from functools import partial
import logging

import voluptuous as vol

from homeassistant.components.device_tracker import PLATFORM_SCHEMA
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import (
    ATTR_LATITUDE, ATTR_LONGITUDE, HTTP_UNPROCESSABLE_ENTITY, STATE_NOT_HOME)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['http']

BEACON_DEV_PREFIX = 'beacon'
CONF_MOBILE_BEACONS = 'mobile_beacons'

LOCATION_ENTRY = '1'
LOCATION_EXIT = '0'

URL = '/api/geofency'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_MOBILE_BEACONS): vol.All(
        cv.ensure_list, [cv.string]),
})


def setup_scanner(hass, config, see, discovery_info=None):
    """Set up an endpoint for the Geofency application."""
    mobile_beacons = config.get(CONF_MOBILE_BEACONS) or []

    hass.http.register_view(GeofencyView(see, mobile_beacons))

    return True


class GeofencyView(HomeAssistantView):
    """View to handle Geofency requests."""

    url = URL
    name = 'api:geofency'

    def __init__(self, see, mobile_beacons):
        """Initialize Geofency url endpoints."""
        self.see = see
        self.mobile_beacons = [slugify(beacon) for beacon in mobile_beacons]

    @asyncio.coroutine
    def post(self, request):
        """Geofency message received."""
        data = yield from request.post()
        return (yield from self._handle(request.app['hass'], data))

    @asyncio.coroutine
    def _handle(self, hass, data):
        """Handle Geofency requests."""
        data = self._validate_data(data)
        if not data:
            return ("Invalid data", HTTP_UNPROCESSABLE_ENTITY)

        if self._is_mobile_beacon(data):
            return (yield from self._set_location(hass, data, None))
        else:
            if data['entry'] == LOCATION_ENTRY:
                location_name = data['name']
            else:
                location_name = STATE_NOT_HOME

            return (yield from self._set_location(hass, data, location_name))

    @staticmethod
    def _validate_data(data):
        """Validate POST payload."""
        data = data.copy()

        required_attributes = ['address', 'device', 'entry',
                               'latitude', 'longitude', 'name']

        valid = True
        for attribute in required_attributes:
            if attribute not in data:
                valid = False
                _LOGGER.error("'%s' not specified in message", attribute)

        if not valid:
            return False

        data['address'] = data['address'].replace('\n', ' ')
        data['device'] = slugify(data['device'])
        data['name'] = slugify(data['name'])

        data[ATTR_LATITUDE] = float(data[ATTR_LATITUDE])
        data[ATTR_LONGITUDE] = float(data[ATTR_LONGITUDE])

        return data

    def _is_mobile_beacon(self, data):
        """Check if we have a mobile beacon."""
        return 'beaconUUID' in data and data['name'] in self.mobile_beacons

    @staticmethod
    def _device_name(data):
        """Return name of device tracker."""
        if 'beaconUUID' in data:
            return "{}_{}".format(BEACON_DEV_PREFIX, data['name'])
        else:
            return data['device']

    @asyncio.coroutine
    def _set_location(self, hass, data, location_name):
        """Fire HA event to set location."""
        device = self._device_name(data)

        yield from hass.async_add_job(
            partial(self.see, dev_id=device,
                    gps=(data[ATTR_LATITUDE], data[ATTR_LONGITUDE]),
                    location_name=location_name,
                    attributes=data))

        return "Setting location for {}".format(device)
