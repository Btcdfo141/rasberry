"""Support for the MAX! Cube LAN Gateway."""
import logging
from socket import timeout
from threading import Lock
import time

from maxcube.cube import MaxCube
import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 62910
DOMAIN = "maxcube"

DATA_KEY = "maxcube"

NOTIFICATION_ID = "maxcube_notification"
NOTIFICATION_TITLE = "Max!Cube gateway setup"

CONF_GATEWAYS = "gateways"
CONF_SHARED = "shared"

CONFIG_GATEWAY = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_SCAN_INTERVAL, default=0): cv.time_period,
        vol.Optional(CONF_SHARED, default=False): cv.boolean,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_GATEWAYS, default={}): vol.All(
                    cv.ensure_list, [CONFIG_GATEWAY]
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    """Establish connection to MAX! Cube."""

    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    connection_failed = 0
    gateways = config[DOMAIN][CONF_GATEWAYS]
    for gateway in gateways:
        host = gateway[CONF_HOST]
        port = gateway[CONF_PORT]
        scan_interval = gateway[CONF_SCAN_INTERVAL].total_seconds()
        shared = gateway[CONF_SHARED]
        if scan_interval == 0:
            scan_interval = 300 if shared else 60
        elif not shared and scan_interval < 60:
            scan_interval = 60
            _LOGGER.warning(
                "Forcing minimum scan interval of 60 seconds in exclusive mode"
            )
        elif shared and scan_interval < 300:
            scan_interval = 300
            _LOGGER.warning(
                "Forcing minimum scan interval of 300 seconds in shared mode"
            )

        try:
            cube = MaxCube(host, port)
            hass.data[DATA_KEY][host] = MaxCubeHandle(
                cube, scan_interval, shared=shared
            )
        except timeout as ex:
            _LOGGER.error("Unable to connect to Max!Cube gateway: %s", str(ex))
            hass.components.persistent_notification.create(
                f"Error: {ex}<br />You will need to restart Home Assistant after fixing.",
                title=NOTIFICATION_TITLE,
                notification_id=NOTIFICATION_ID,
            )
            connection_failed += 1

    if connection_failed >= len(gateways):
        return False

    load_platform(hass, "climate", DOMAIN, {}, config)
    load_platform(hass, "binary_sensor", DOMAIN, {}, config)

    return True


class MaxCubeHandle:
    """Keep the cube instance in one place and centralize the update."""

    def __init__(self, cube, scan_interval, *, shared: bool):
        """Initialize the Cube Handle."""
        self.cube = cube
        self.scan_interval = scan_interval
        self.shared = shared
        self.mutex = Lock()
        self._updatets = time.monotonic()
        if shared:
            _LOGGER.warning(
                "Enabling shared mode may cause MAX! Cube to factory reset. Check https://github.com/hackercowboy/python-maxcube-api/issues/12"
            )
            self.cube.disconnect()

    def update(self):
        """Pull the latest data from the MAX! Cube."""
        # Acquire mutex to prevent simultaneous update from multiple threads
        with self.mutex:
            # Only update every update_interval
            if (time.monotonic() - self._updatets) >= self.scan_interval:
                _LOGGER.debug("Updating")

                try:
                    self.cube.update()
                    if self.shared:
                        self.cube.disconnect()
                except timeout:
                    _LOGGER.error("Max!Cube connection failed")
                    return False

                self._updatets = time.monotonic()
            else:
                _LOGGER.debug("Skipping update")
