"""Support for (EMEA/EU-based) Honeywell evohome systems.

Support for a temperature control system (TCS, controller) with 0+ heating
zones (e.g. TRVs, relays) and, optionally, a DHW controller.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/evohome/
"""

# Glossary:
#   TCS - temperature control system (a.k.a. Controller, Parent), which can
#   have up to 13 Children:
#     0-12 Heating zones (a.k.a. Zone), and
#     0-1 DHW controller, (a.k.a. Boiler)
# The TCS & Zones are implemented as Climate devices, Boiler as a WaterHeater

import logging

from requests.exceptions import HTTPError
import voluptuous as vol

from homeassistant.components.climate.evohome import EvoController, EvoZone
from homeassistant.const import (
    CONF_SCAN_INTERVAL, CONF_USERNAME, CONF_PASSWORD,
    EVENT_HOMEASSISTANT_START,
    HTTP_BAD_REQUEST, HTTP_SERVICE_UNAVAILABLE, HTTP_TOO_MANY_REQUESTS
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

REQUIREMENTS = ['https://github.com/watchforstock/evohome-client/archive/master.zip#evohomeclient==0.2.8']  # noqa E501

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'evohome'
DATA_EVOHOME = 'data_' + DOMAIN
DISPATCHER_EVOHOME = 'dispatcher_' + DOMAIN

CONF_LOCATION_IDX = 'location_idx'
SCAN_INTERVAL_DEFAULT = 300

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_LOCATION_IDX, default=0): cv.positive_int,
    }),
}, extra=vol.ALLOW_EXTRA)

# These are used to help prevent E501 (line too long) violations.
GWS = 'gateways'
TCS = 'temperatureControlSystems'


def setup(hass, config):
    """Create a (EMEA/EU-based) Honeywell evohome system.

    Currently, only the Controller and the Zones are implemented here.
    """
    evo_data = hass.data[DATA_EVOHOME] = {}
    evo_data['timers'] = {}

    evo_data['params'] = dict(config[DOMAIN])
    evo_data['params'][CONF_SCAN_INTERVAL] = SCAN_INTERVAL_DEFAULT

    from evohomeclient2 import EvohomeClient

    _LOGGER.debug("setup(): API call [4 request(s)]: client.__init__()...")
    try:
        client = EvohomeClient(
            evo_data['params'][CONF_USERNAME],
            evo_data['params'][CONF_PASSWORD],
            debug=False
        )

    except HTTPError as err:
        if err.response.status_code == HTTP_BAD_REQUEST:
            _LOGGER.error(
                "setup(): Failed to connect with the vendor's web servers. "
                "Check your username (%s), and password are correct."
                "Unable to continue. Resolve any errors and restart HA.",
                evo_data['params'][CONF_USERNAME]
            )

        elif err.response.status_code == HTTP_SERVICE_UNAVAILABLE:
            _LOGGER.error(
                "setup(): Failed to connect with the vendor's web servers. "
                "The server is not contactable. Unable to continue. "
                "Resolve any errors and restart HA."
            )

        elif err.response.status_code == HTTP_TOO_MANY_REQUESTS:
            _LOGGER.error(
                "setup(): Failed to connect with the vendor's web servers. "
                "You have exceeded the api rate limit. Unable to continue. "
                "Wait a while (say 10 minutes) and restart HA."
            )

        else:
            raise  # we dont expect/handle any other HTTPErrors

        return False  # unable to continue

    finally:  # Redact username, password as no longer needed
        evo_data['params'][CONF_USERNAME] = 'REDACTED'
        evo_data['params'][CONF_PASSWORD] = 'REDACTED'

    evo_data['client'] = client

    # Redact any installation data we'll never need
    if client.installation_info[0]['locationInfo']['locationId'] != 'REDACTED':
        for loc in client.installation_info:
            loc['locationInfo']['streetAddress'] = 'REDACTED'
            loc['locationInfo']['city'] = 'REDACTED'
            loc['locationInfo']['locationOwner'] = 'REDACTED'
            loc[GWS][0]['gatewayInfo'] = 'REDACTED'

    # Pull down the installation configuration
    loc_idx = evo_data['params'][CONF_LOCATION_IDX]

    try:
        evo_data['config'] = client.installation_info[loc_idx]

    except IndexError:
        _LOGGER.warning(
            "setup(): Parameter '%s'=%s , is outside its range (0-%s)",
            CONF_LOCATION_IDX,
            loc_idx,
            len(client.installation_info) - 1
        )

        return False  # unable to continue

    if _LOGGER.isEnabledFor(logging.DEBUG):
        tmp_loc = dict(evo_data['config'])
        tmp_loc['locationInfo']['postcode'] = 'REDACTED'
        if 'dhw' in tmp_loc[GWS][0][TCS][0]:  # if this location has DHW...
            tmp_loc[GWS][0][TCS][0]['dhw'] = '...'

        _LOGGER.debug("setup(): evo_data['config']=%s", tmp_loc)

    # evohomeclient has exposed no means of accessing non-default location
    # (i.e. loc_idx > 0) other than using a protected member, such as below
    tcs_obj_ref = client.locations[loc_idx]._gateways[0]._control_systems[0]    # noqa E501; pylint: disable=protected-access

    _LOGGER.debug(
        "setup(): Found Controller, id=%s, name=%s (location_idx=%s)",
        tcs_obj_ref.systemId + " [" + tcs_obj_ref.modelType + "]",
        tcs_obj_ref.location.name,
        loc_idx
    )

    evo_data['parent'] = EvoController(evo_data, client, tcs_obj_ref)
    evo_data['children'] = zones = []

    for z in tcs_obj_ref.zones:                                                 # noqa E501; pylint: disable=invalid-name
        zone_obj_ref = tcs_obj_ref.zones[z]
        _LOGGER.debug(
            "setup(): Found Zone, id=%s, name=%s",
            zone_obj_ref.zoneId + " [" + zone_obj_ref.zone_type + "]",
            zone_obj_ref.name
        )
        zones.append(EvoZone(evo_data, client, zone_obj_ref))

    hass.async_create_task(
        async_load_platform(hass, 'climate', DOMAIN, {}, config))

    return True