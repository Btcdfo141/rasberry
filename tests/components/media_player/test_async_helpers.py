"""The tests for the Async Media player helper functions."""

import pytest

import homeassistant.components.media_player as mp
from homeassistant.const import STATE_OFF, STATE_ON, STATE_PAUSED, STATE_PLAYING


class AsyncMediaPlayer(mp.MediaPlayerEntity):
    """Async media player test class."""

    def __init__(self, hass):
        """Initialize the test media player."""
        self.hass = hass
        self._volume = 0
        self._state = STATE_OFF

    @property
    def state(self):
        """State of the player."""
        return self._state

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return (
            mp.const.SUPPORT_VOLUME_SET
            | mp.const.SUPPORT_PLAY
            | mp.const.SUPPORT_PAUSE
            | mp.const.SUPPORT_TURN_OFF
            | mp.const.SUPPORT_TURN_ON
        )

    async def async_set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        self._volume = volume

    async def async_media_play(self):
        """Send play command."""
        self._state = STATE_PLAYING

    async def async_media_pause(self):
        """Send pause command."""
        self._state = STATE_PAUSED

    async def async_turn_on(self):
        """Turn the media player on."""
        self._state = STATE_ON

    async def async_turn_off(self):
        """Turn the media player off."""
        self._state = STATE_OFF


@pytest.fixture
def player(hass):
    """Set up async player to be run when tests are started."""
    return AsyncMediaPlayer(hass)


async def test_volume_up(hass, player):
    """Test the volume_up helper function."""
    assert player.volume_level == 0

    await player.async_set_volume_level(0.5)
    assert player.volume_level == 0.5

    await player.async_volume_up()
    assert player.volume_level == 0.6


async def test_volume_down(hass, player):
    """Test the volume_down helper function."""
    assert player.volume_level == 0

    await player.async_set_volume_level(0.5)
    assert player.volume_level == 0.5

    await player.async_volume_down()
    assert player.volume_level == 0.4


async def test_media_play_pause(hass, player):
    """Test the media_play_pause helper function."""
    assert player.state == STATE_OFF

    await player.async_media_play_pause()
    assert player.state == STATE_PLAYING

    await player.async_media_play_pause()
    assert player.state == STATE_PAUSED


async def test_toggle(hass, player):
    """Test the toggle helper function."""
    assert player.state == STATE_OFF

    await player.async_toggle()
    assert player.state == STATE_ON

    await player.async_toggle()
    assert player.state == STATE_OFF
