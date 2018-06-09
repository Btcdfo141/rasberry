"""
Support for the Unitymedia Horizon HD Recorder.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/media_player.horizon/
"""

from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerDevice, PLATFORM_SCHEMA, MEDIA_TYPE_CHANNEL,
    SUPPORT_NEXT_TRACK, SUPPORT_TURN_ON, SUPPORT_TURN_OFF, SUPPORT_PAUSE,
    SUPPORT_PLAY, SUPPORT_PLAY_MEDIA, SUPPORT_PREVIOUS_TRACK)
from homeassistant.const import (CONF_HOST, CONF_NAME, CONF_PORT, STATE_OFF,
                                 STATE_PAUSED, STATE_PLAYING)
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv
import homeassistant.util as util

REQUIREMENTS = ['einder==0.3.1']

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Horizon"
DEFAULT_PORT = 5900

MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=1)
MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)

SUPPORT_HORIZON = SUPPORT_NEXT_TRACK | SUPPORT_PAUSE | SUPPORT_PLAY | \
                  SUPPORT_PLAY_MEDIA | SUPPORT_PREVIOUS_TRACK | \
                  SUPPORT_TURN_ON | SUPPORT_TURN_OFF

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Horizon platform."""
    from einder import Client, keys
    from einder.exceptions import AuthenticationError

    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    port = config.get(CONF_PORT)

    try:
        client = Client(host, port=port)
    except AuthenticationError as msg:
        _LOGGER.error("Authentication to %s at %s failed: %s", name, host, msg)
        return
    except OSError as msg:
        # occurs if horizon box is offline
        _LOGGER.error("Connection to %s at %s failed: %s", name, host, msg)
        raise PlatformNotReady

    _LOGGER.info("Connection to %s at %s established", name, host)

    add_devices([HorizonDevice(client, name, keys)], True)


class HorizonDevice(MediaPlayerDevice):
    """Representation of a Horizon HD Recorder."""

    def __init__(self, client, name, keys):
        """Initialize the remote."""
        self._client = client
        self._name = name
        self._state = False
        self._keys = keys

    @property
    def name(self):
        """Return the name of the remote."""
        return self._name

    @property
    def client(self):
        """Return the Horizon client object."""
        return self._client

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def keys(self):
        """Return the predefined keys."""
        return self._keys

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_HORIZON

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update(self):
        """Update State using the media server running on the Horizon."""
        if self._client.is_powered_on():
            self._state = STATE_PLAYING
        else:
            self._state = STATE_OFF

    def turn_on(self):
        """Turn the device on."""
        if self._state is STATE_OFF:
            self._send_key(self._keys.POWER)

    def turn_off(self):
        """Turn the device off."""
        if self._state is not STATE_OFF:
            self._send_key(self._keys.POWER)

    def media_previous_track(self):
        """Channel down."""
        self._send_key(self._keys.CHAN_DOWN)
        self._state = STATE_PLAYING

    def media_next_track(self):
        """Channel up."""
        self._send_key(self._keys.CHAN_UP)
        self._state = STATE_PLAYING

    def media_play(self):
        """Send play command."""
        self._send_key(self._keys.PAUSE)
        self._state = STATE_PLAYING

    def media_pause(self):
        """Send pause command."""
        self._send_key(self._keys.PAUSE)
        self._state = STATE_PAUSED

    def media_play_pause(self):
        """Send play/pause command."""
        self._send_key(self._keys.PAUSE)
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING
        else:
            self._state = STATE_PAUSED

    def play_media(self, media_type, media_id, **kwargs):
        """Play media / switch to channel."""
        if MEDIA_TYPE_CHANNEL == media_type and isinstance(int(media_id), int):
            self._select_channel(media_id)
            self._state = STATE_PLAYING
        else:
            _LOGGER.error("Invalid type %s or channel %d. Supported type: %s",
                          media_type, media_id, MEDIA_TYPE_CHANNEL)

    def _select_channel(self, channel):
        """Select a channel (taken from einder library, thx)."""
        for i in str(channel):
            key = int(i) + 0xe300
            self._send_key(key)

    def _send_key(self, key):
        """Send a key to the Horizon device."""
        try:
            self._client.send_key(key)
        except OSError as msg:
            _LOGGER.error("%s disconnected: %s", self._name, msg)
            self._reconnect()
            self._client.send_key(key)

    def _reconnect(self):
        """Reconnecting to the Horizon after a disconnect."""
        from einder.exceptions import AuthenticationError

        # graceful disconnect
        self._client.disconnect()

        try:
            self._client.connect()
            self._client.authorize()
        except (AuthenticationError, OSError) as msg:
            _LOGGER.error("Connection to %s failed: %s", self._name, msg)
            return False
