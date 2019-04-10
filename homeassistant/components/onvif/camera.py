"""
Support for ONVIF Cameras with FFmpeg as decoder.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/camera.onvif/
"""
import asyncio
import logging
import os

import voluptuous as vol
import datetime as dt

from homeassistant.const import (
    CONF_NAME, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT,
    ATTR_ENTITY_ID)
from homeassistant.components.camera import (
    Camera, PLATFORM_SCHEMA, SUPPORT_STREAM)
from homeassistant.components.camera.const import DOMAIN
from homeassistant.components.ffmpeg import (
    DATA_FFMPEG, CONF_EXTRA_ARGUMENTS)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import (
    async_aiohttp_proxy_stream)
from homeassistant.helpers.service import extract_entity_ids
from onvif import ONVIFCamera

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['onvif-zeep==0.2.12',
                'zeep==3.0.0']
DEPENDENCIES = ['ffmpeg']
DEFAULT_NAME = 'ONVIF Camera'
DEFAULT_PORT = 5000
DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD = '888888'
DEFAULT_ARGUMENTS = '-pred 1'
DEFAULT_PROFILE = 0

CONF_PROFILE = "profile"

ATTR_PAN = "pan"
ATTR_TILT = "tilt"
ATTR_ZOOM = "zoom"

DIR_UP = "UP"
DIR_DOWN = "DOWN"
DIR_LEFT = "LEFT"
DIR_RIGHT = "RIGHT"
ZOOM_OUT = "ZOOM_OUT"
ZOOM_IN = "ZOOM_IN"
PTZ_NONE = "NONE"

SERVICE_PTZ = "onvif_ptz"

ONVIF_DATA = "onvif"
ENTITIES = "entities"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): cv.string,
    vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_EXTRA_ARGUMENTS, default=DEFAULT_ARGUMENTS): cv.string,
    vol.Optional(CONF_PROFILE, default=DEFAULT_PROFILE):
        vol.All(vol.Coerce(int), vol.Range(min=0)),
})

SERVICE_PTZ_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.entity_ids,
    ATTR_PAN: vol.In([DIR_LEFT, DIR_RIGHT, PTZ_NONE]),
    ATTR_TILT: vol.In([DIR_UP, DIR_DOWN, PTZ_NONE]),
    ATTR_ZOOM: vol.In([ZOOM_OUT, ZOOM_IN, PTZ_NONE])
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up a ONVIF camera."""

    _LOGGER.debug("Setting up the ONVIF camera platform")
    
    def handle_ptz(service):
        """Handle PTZ service call."""
        pan = service.data.get(ATTR_PAN, None)
        tilt = service.data.get(ATTR_TILT, None)
        zoom = service.data.get(ATTR_ZOOM, None)
        all_cameras = hass.data[ONVIF_DATA][ENTITIES]
        entity_ids = extract_entity_ids(hass, service)
        target_cameras = []
        if not entity_ids:
            target_cameras = all_cameras
        else:
            target_cameras = [camera for camera in all_cameras
                              if camera.entity_id in entity_ids]
        for camera in target_cameras:
            camera.perform_ptz(pan, tilt, zoom)

    hass.services.register(DOMAIN, SERVICE_PTZ, handle_ptz,
                           schema=SERVICE_PTZ_SCHEMA)
    add_entities([ONVIFHassCamera(hass, config)])


class ONVIFHassCamera(Camera):
    """An implementation of an ONVIF camera."""

    def __init__(self, hass, config):
        """Initialize a ONVIF camera."""
        super().__init__()
        
        import onvif
        import zeep

        # Note: important imports foor zeep and onvif-zeep, see https://github.com/FalkTannhaeuser/python-onvif-zeep/issues/4#issuecomment-370173336
        def zeep_pythonvalue(self, xmlvalue):
            return xmlvalue
        zeep.xsd.simple.AnySimpleType.pythonvalue = zeep_pythonvalue

        _LOGGER.debug("Setting up the ONVIF camera component")

        self._username = config.get(CONF_USERNAME)
        self._password = config.get(CONF_PASSWORD)
        self._host = config.get(CONF_HOST)
        self._port = config.get(CONF_PORT)
        self._name = config.get(CONF_NAME)
        self._ffmpeg_arguments = config.get(CONF_EXTRA_ARGUMENTS)
        self._profile_index = config.get(CONF_PROFILE)
        self._input = None

        _LOGGER.debug("Setting up the ONVIF camera device @ '%s:%s'",
                      self._host,
                      self._port)

        self._camera = ONVIFCamera(self._host,
                                   self._port,
                                   self._username,
                                   self._password,
                                   '{}/wsdl/'
                                   .format(os.path.dirname(onvif.__file__)))

        _LOGGER.debug("Setting up the ONVIF device management service")

        self._devicemgmt = self._camera.create_devicemgmt_service()

        _LOGGER.debug("Retrieving current camera date/time")

        system_date = dt.datetime.utcnow()
        cdate = self._devicemgmt.GetSystemDateAndTime().UTCDateTime
        cam_date = dt.datetime(cdate.Date.Year, cdate.Date.Month,
                               cdate.Date.Day, cdate.Time.Hour,
                               cdate.Time.Minute, cdate.Time.Second)

        _LOGGER.debug("Camera date/time: %s",
                      cam_date)

        _LOGGER.debug("System date/time: %s",
                      system_date)

        dt_diff = cam_date - system_date
        dt_diff_seconds = dt_diff.total_seconds()

        if dt_diff_seconds > 5:
            _LOGGER.warning("The date/time on the camera is '%s', "
                            "which is different from the system '%s', "
                            "this could lead to authentication issues",
                            cam_date,
                            system_date)

        _LOGGER.debug("Setting up the ONVIF media service")

        self._media_service = self._camera.create_media_service()

        _LOGGER.debug("Setting up the ONVIF PTZ service")

        self._ptz_service = self._camera.create_ptz_service()

        _LOGGER.debug("Completed set up of the ONVIF camera component")

    def obtain_input_uri(self):
        """Set the input uri for the camera."""
        from onvif import exceptions
        _LOGGER.debug("Connecting with ONVIF Camera: %s on port %s",
                      self._host, self._port)

        try:
            _LOGGER.debug("Retrieving profiles")

            profiles = self._media_service.GetProfiles()

            _LOGGER.debug("Retrieved '%d' profiles",
                          len(profiles))

            if self._profile_index >= len(profiles):
                _LOGGER.warning("ONVIF Camera '%s' doesn't provide profile %d."
                                " Using the last profile.",
                                self._name, self._profile_index)
                self._profile_index = -1

            _LOGGER.debug("Using profile index '%d'",
                          self._profile_index)

            _LOGGER.debug("Retrieving stream uri")

            req = self._media_service.create_type('GetStreamUri')
            req.ProfileToken = profiles[self._profile_index].token
            req.StreamSetup = {'Stream': 'RTP-Unicast',
                               'Transport': {'Protocol': 'RTSP'}}

            uri_no_auth = self._media_service.GetStreamUri(req).Uri
            uri_for_log = uri_no_auth.replace(
                'rtsp://', 'rtsp://<user>:<password>@', 1)
            self._input = uri_no_auth.replace(
                'rtsp://', 'rtsp://{}:{}@'.format(self._username,
                                                  self._password), 1)

            _LOGGER.debug(
                "ONVIF Camera Using the following URL for %s: %s",
                self._name, uri_for_log)

            # we won't need the media service anymore
            self._media_service = None
        except exceptions.ONVIFError as err:
            _LOGGER.debug("Couldn't setup camera '%s'. Error: %s",
                          self._name, err)
            return

    def perform_ptz(self, pan, tilt, zoom):
        """Perform a PTZ action on the camera."""
        from onvif import exceptions
        if self._ptz_service:
            pan_val = 1 if pan == DIR_RIGHT else -1 if pan == DIR_LEFT else 0
            tilt_val = 1 if tilt == DIR_UP else -1 if tilt == DIR_DOWN else 0
            zoom_val = 1 if zoom == ZOOM_IN else -1 if zoom == ZOOM_OUT else 0
            req = {"Velocity": {
                "PanTilt": {"_x": pan_val, "_y": tilt_val},
                "Zoom": {"_x": zoom_val}}}
            try:
                self._ptz_service.ContinuousMove(req)
            except exceptions.ONVIFError as err:
                if "Bad Request" in err.reason:
                    self._ptz_service = None
                    _LOGGER.debug("Camera '%s' doesn't support PTZ.",
                                  self._name)
        else:
            _LOGGER.debug("Camera '%s' doesn't support PTZ.", self._name)

    async def async_added_to_hass(self):
        """Handle entity addition to hass."""
        if ONVIF_DATA not in self.hass.data:
            self.hass.data[ONVIF_DATA] = {}
            self.hass.data[ONVIF_DATA][ENTITIES] = []
        self.hass.data[ONVIF_DATA][ENTITIES].append(self)
        await self.hass.async_add_executor_job(self.obtain_input_uri)

    async def async_camera_image(self):
        """Return a still image response from the camera."""
        from haffmpeg.tools import ImageFrame, IMAGE_JPEG

        if not self._input:
            await self.hass.async_add_executor_job(self.obtain_input_uri)
            if not self._input:
                return None

        ffmpeg = ImageFrame(
            self.hass.data[DATA_FFMPEG].binary, loop=self.hass.loop)

        image = await asyncio.shield(ffmpeg.get_image(
            self._input, output_format=IMAGE_JPEG,
            extra_cmd=self._ffmpeg_arguments), loop=self.hass.loop)
        return image

    async def handle_async_mjpeg_stream(self, request):
        """Generate an HTTP MJPEG stream from the camera."""
        from haffmpeg.camera import CameraMjpeg

        if not self._input:
            await self.hass.async_add_executor_job(self.obtain_input_uri)
            if not self._input:
                return None

        ffmpeg_manager = self.hass.data[DATA_FFMPEG]
        stream = CameraMjpeg(ffmpeg_manager.binary,
                             loop=self.hass.loop)
        await stream.open_camera(
            self._input, extra_cmd=self._ffmpeg_arguments)

        try:
            stream_reader = await stream.get_reader()
            return await async_aiohttp_proxy_stream(
                self.hass, request, stream_reader,
                ffmpeg_manager.ffmpeg_stream_content_type)
        finally:
            await stream.close()

    @property
    def supported_features(self):
        """Return supported features."""
        if self._input:
            return SUPPORT_STREAM
        return 0

    @property
    def stream_source(self):
        """Return the stream source."""
        return self._input

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name
