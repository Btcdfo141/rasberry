"""Constants for the swiss_public_transport integration."""

from typing import Final

DOMAIN = "swiss_public_transport"

CONF_DESTINATION = "to"
CONF_START = "from"

DEFAULT_NAME = "Next Destination"

SENSOR_CONNECTIONS_COUNT = 3
SENSOR_CONNECTIONS_MAX = 15


PLACEHOLDERS = {
    "stationboard_url": "http://transport.opendata.ch/examples/stationboard.html",
    "opendata_url": "http://transport.opendata.ch",
}

ATTR_LIMIT: Final = "limit"

SERVICE_FETCH_CONNECTIONS = "fetch_connections"
