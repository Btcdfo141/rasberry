"""
homeassistant.components.media_player.chromecast
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides functionality to interact with Cast devices on the network.

WARNING: This platform is currently not working due to a changed Cast API
"""
import logging

try:
    import pychromecast
    import pychromecast.controllers.youtube as youtube
except ImportError:
    # We will throw error later
    pass

from homeassistant.components.media_player import (
    MediaPlayerDevice, STATE_NO_APP, ATTR_MEDIA_STATE,
    ATTR_MEDIA_CONTENT_ID, ATTR_MEDIA_TITLE, ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_ALBUM, ATTR_MEDIA_IMAGE_URL, ATTR_MEDIA_DURATION,
    ATTR_MEDIA_VOLUME, MEDIA_STATE_PLAYING, MEDIA_STATE_PAUSED, MEDIA_STATE_STOPPED)


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up the cast platform. """
    logger = logging.getLogger(__name__)

    try:
        # pylint: disable=redefined-outer-name
        import pychromecast
    except ImportError:
        logger.exception(("Failed to import pychromecast. "
                          "Did you maybe not install the 'pychromecast' "
                          "dependency?"))

        return

    if discovery_info:
        hosts = [discovery_info[0]]

    else:
        hosts = pychromecast.discover_chromecasts()

    casts = []

    for host in hosts:
        try:
            casts.append(CastDevice(host))
        except pychromecast.ChromecastConnectionError:
            pass

    add_devices(casts)


class CastDevice(MediaPlayerDevice):
    """ Represents a Cast device on the network. """

    def __init__(self, host):
        self.cast = pychromecast.Chromecast(host)
        self.youtube = youtube.YouTubeController()
        self.cast.register_handler(self.youtube)

    @property
    def name(self):
        """ Returns the name of the device. """
        return self.cast.device.friendly_name

    @property
    def state(self):
        """ Returns the state of the device. """
        status = self.cast.status

        if self.cast.app_display_name:
            return self.cast.app_display_name
        else:
            return STATE_NO_APP

    @property
    def state_attributes(self):
        """ Returns the state attributes. """
        mc = self.cast.media_controller;

        if mc:
            state_attr = {}

            if mc.is_playing:
                state_attr[ATTR_MEDIA_STATE] = MEDIA_STATE_PLAYING
            elif mc.is_paused:
                state_attr[ATTR_MEDIA_STATE] = MEDIA_STATE_PAUSED
            elif mc.is_idle:
                state_attr[ATTR_MEDIA_STATE] = MEDIA_STATE_STOPPED

            media_status = self.cast.status

            if media_status:

                """ These status properties seem not to be present anymore in pychromecast """
                #if ramp.content_id:
                #    state_attr[ATTR_MEDIA_CONTENT_ID] = mc.ramp.content_id

                #if ramp.title:
                #    state_attr[ATTR_MEDIA_TITLE] = ramp.title

                #if ramp.artist:
                #    state_attr[ATTR_MEDIA_ARTIST] = ramp.artist

                #if ramp.album:
                #    state_attr[ATTR_MEDIA_ALBUM] = ramp.album

                #if ramp.image_url:
                #    state_attr[ATTR_MEDIA_IMAGE_URL] = ramp.image_url

                if hasattr(media_status, 'duration'):
                    state_attr[ATTR_MEDIA_DURATION] = media_status.duration

                state_attr[ATTR_MEDIA_VOLUME] = media_status.volume_level

            return state_attr

    def turn_off(self):
        """ Service to exit any running app on the specimedia player ChromeCast and
        shows idle screen. Will quit all ChromeCasts if nothing specified.
        """
        self.cast.quit_app()

    def volume_up(self):
        """ Service to send the chromecast the command for volume up. """
        self.cast.volume_up()

    def volume_down(self):
        """ Service to send the chromecast the command for volume down. """
        self.cast.volume_down()

    def media_play_pause(self):
        """ Service to send the chromecast the command for play/pause. """
        media_state = self.state_attributes[ATTR_MEDIA_STATE]
        if media_state == MEDIA_STATE_STOPPED or media_state == MEDIA_STATE_PAUSED:
            self.media_pause()
        elif media_state == MEDIA_STATE_PLAYING:
            self.media_play()

    def media_play(self):
        """ Service to send the chromecast the command for play/pause. """
        if self.state_attributes[ATTR_MEDIA_STATE] == MEDIA_STATE_STOPPED:
            self.media_play_pause()

    def media_pause(self):
        """ Service to send the chromecast the command for play/pause. """
        if self.state_attributes[ATTR_MEDIA_STATE] == MEDIA_STATE_PLAYING:
            self.media_play_pause()

    """ This one seems not to be present anymore in pychromecast, needs porting or cleanup """
    #def media_next_track(self):
    #    """ Service to send the chromecast the command for next track. """
    #    ramp = self.cast.get_protocol(pychromecast.PROTOCOL_RAMP)

    #    if ramp:
    #        ramp.next()

    def play_youtube_video(self, video_id):
        """ Plays specified video_id on the Chromecast's YouTube channel. """
        self.youtube.play_video(video_id)