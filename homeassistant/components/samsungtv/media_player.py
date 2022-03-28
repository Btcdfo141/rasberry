"""Support for interface with an Samsung TV."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
import contextlib
from datetime import datetime, timedelta
from typing import Any

from async_upnp_client.aiohttp import AiohttpSessionRequester
from async_upnp_client.client import UpnpDevice, UpnpService
from async_upnp_client.client_factory import UpnpFactory
from async_upnp_client.exceptions import UpnpActionResponseError, UpnpConnectionError
import voluptuous as vol
from wakeonlan import send_magic_packet

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_APP,
    MEDIA_TYPE_CHANNEL,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_NAME, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_component
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.script import Script
from homeassistant.util import dt as dt_util

from .bridge import SamsungTVBridge, SamsungTVWSBridge
from .const import (
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_ON_ACTION,
    CONF_SSDP_RENDERING_CONTROL_LOCATION,
    DEFAULT_NAME,
    DOMAIN,
    LOGGER,
    UPNP_SVC_RENDERING_CONTROL,
)

SOURCES = {"TV": "KEY_TV", "HDMI": "KEY_HDMI"}

SUPPORT_SAMSUNGTV = (
    SUPPORT_PAUSE
    | SUPPORT_VOLUME_STEP
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_SELECT_SOURCE
    | SUPPORT_NEXT_TRACK
    | SUPPORT_TURN_OFF
    | SUPPORT_PLAY
    | SUPPORT_PLAY_MEDIA
)

# Since the TV will take a few seconds to go to sleep
# and actually be seen as off, we need to wait just a bit
# more than the next scan interval
SCAN_INTERVAL_PLUS_OFF_TIME = entity_component.DEFAULT_SCAN_INTERVAL + timedelta(
    seconds=5
)

# Max delay waiting for app_list to return, as some TVs simply ignore the request
APP_LIST_DELAY = 3


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Samsung TV from a config entry."""
    bridge = hass.data[DOMAIN][entry.entry_id]

    host = entry.data[CONF_HOST]
    on_script = None
    data = hass.data[DOMAIN]
    if turn_on_action := data.get(host, {}).get(CONF_ON_ACTION):
        on_script = Script(
            hass, turn_on_action, entry.data.get(CONF_NAME, DEFAULT_NAME), DOMAIN
        )

    async_add_entities([SamsungTVDevice(bridge, entry, on_script)], True)


class SamsungTVDevice(MediaPlayerEntity):
    """Representation of a Samsung TV."""

    _attr_source_list: list[str]

    def __init__(
        self,
        bridge: SamsungTVBridge,
        config_entry: ConfigEntry,
        on_script: Script | None,
    ) -> None:
        """Initialize the Samsung device."""
        self._config_entry = config_entry
        self._host: str | None = config_entry.data[CONF_HOST]
        self._mac: str | None = config_entry.data.get(CONF_MAC)
        self._ssdp_rendering_control_location = config_entry.data.get(
            CONF_SSDP_RENDERING_CONTROL_LOCATION
        )
        self._on_script = on_script
        # Assume that the TV is in Play mode
        self._playing: bool = True

        self._attr_name: str | None = config_entry.data.get(CONF_NAME)
        self._attr_state: str | None = None
        self._attr_unique_id = config_entry.unique_id
        self._attr_is_volume_muted: bool = False
        self._attr_device_class = MediaPlayerDeviceClass.TV
        self._attr_source_list = list(SOURCES)
        self._app_list: dict[str, str] | None = None
        self._app_list_event: asyncio.Event = asyncio.Event()

        self._attr_supported_features = SUPPORT_SAMSUNGTV
        if self._on_script or self._mac:
            # Add turn-on if on_script or mac is available
            self._attr_supported_features |= SUPPORT_TURN_ON
        if self._ssdp_rendering_control_location:
            self._attr_supported_features |= SUPPORT_VOLUME_SET

        self._attr_device_info = DeviceInfo(
            name=self.name,
            manufacturer=config_entry.data.get(CONF_MANUFACTURER),
            model=config_entry.data.get(CONF_MODEL),
        )
        if self.unique_id:
            self._attr_device_info["identifiers"] = {(DOMAIN, self.unique_id)}
        if self._mac:
            self._attr_device_info["connections"] = {
                (CONNECTION_NETWORK_MAC, self._mac)
            }

        # Mark the end of a shutdown command (need to wait 15 seconds before
        # sending the next command to avoid turning the TV back ON).
        self._end_of_power_off: datetime | None = None
        self._bridge = bridge
        self._auth_failed = False
        self._bridge.register_reauth_callback(self.access_denied)
        self._bridge.register_app_list_callback(self._app_list_callback)

        self._upnp_device: UpnpDevice | None = None

    def _update_sources(self) -> None:
        self._attr_source_list = list(SOURCES)
        if app_list := self._app_list:
            self._attr_source_list.extend(app_list)

    def _app_list_callback(self, app_list: dict[str, str]) -> None:
        """App list callback."""
        self._app_list = app_list
        self._update_sources()
        self._app_list_event.set()

    def access_denied(self) -> None:
        """Access denied callback."""
        LOGGER.debug("Access denied in getting remote object")
        self._auth_failed = True
        self.hass.create_task(
            self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": SOURCE_REAUTH,
                    "entry_id": self._config_entry.entry_id,
                },
                data=self._config_entry.data,
            )
        )

    async def async_update(self) -> None:
        """Update state of device."""
        if self._auth_failed or self.hass.is_stopping:
            return
        if self._power_off_in_progress():
            self._attr_state = STATE_OFF
        else:
            self._attr_state = (
                STATE_ON if await self._bridge.async_is_on() else STATE_OFF
            )

        if self._attr_state != STATE_ON:
            return

        startup_tasks: list[Coroutine[Any, Any, None]] = []

        if not self._app_list_event.is_set():
            startup_tasks.append(self._async_startup_app_list())

        if not self._upnp_device and self._ssdp_rendering_control_location:
            startup_tasks.append(self._async_startup_upnp())

        if startup_tasks:
            await asyncio.gather(*startup_tasks)

        if not (service := self._get_upnp_service()):
            return

        get_volume, get_mute = await asyncio.gather(
            service.action("GetVolume").async_call(InstanceID=0, Channel="Master"),
            service.action("GetMute").async_call(InstanceID=0, Channel="Master"),
        )
        LOGGER.debug("Upnp GetVolume on %s: %s", self._host, get_volume)
        if (volume_level := get_volume.get("CurrentVolume")) is not None:
            self._attr_volume_level = volume_level / 100
        LOGGER.debug("Upnp GetMute on %s: %s", self._host, get_mute)
        if (is_muted := get_mute.get("CurrentMute")) is not None:
            self._attr_is_volume_muted = is_muted

    async def _async_startup_app_list(self) -> None:
        await self._bridge.async_request_app_list()
        if self._app_list_event.is_set():
            # The try+wait_for is a bit expensive so we should try not to
            # enter it unless we have to (Python 3.11 will have zero cost try)
            return
        try:
            await asyncio.wait_for(self._app_list_event.wait(), APP_LIST_DELAY)
        except asyncio.TimeoutError as err:
            # No need to try again
            self._app_list_event.set()
            LOGGER.debug(
                "Failed to load app list from %s: %s", self._host, err.__repr__()
            )

    async def _async_startup_upnp(self) -> None:
        assert self._ssdp_rendering_control_location is not None
        if self._upnp_device is None:
            session = async_get_clientsession(self.hass)
            upnp_requester = AiohttpSessionRequester(session)
            upnp_factory = UpnpFactory(upnp_requester)
            with contextlib.suppress(UpnpConnectionError):
                self._upnp_device = await upnp_factory.async_create_device(
                    self._ssdp_rendering_control_location
                )

    def _get_upnp_service(self, log: bool = False) -> UpnpService | None:
        if self._upnp_device is None:
            if log:
                LOGGER.info("Upnp services are not available on %s", self._host)
            return None

        if service := self._upnp_device.services.get(UPNP_SVC_RENDERING_CONTROL):
            return service

        if log:
            LOGGER.info(
                "Upnp service %s is not available on %s",
                UPNP_SVC_RENDERING_CONTROL,
                self._host,
            )
        return None

    async def _async_launch_app(self, app_id: str) -> None:
        """Send launch_app to the tv."""
        if self._power_off_in_progress():
            LOGGER.info("TV is powering off, not sending launch_app command")
            return
        assert isinstance(self._bridge, SamsungTVWSBridge)
        await self._bridge.async_launch_app(app_id)

    async def _async_send_keys(self, keys: list[str]) -> None:
        """Send a key to the tv and handles exceptions."""
        assert keys
        if self._power_off_in_progress() and keys[0] != "KEY_POWEROFF":
            LOGGER.info("TV is powering off, not sending keys: %s", keys)
            return
        await self._bridge.async_send_keys(keys)

    def _power_off_in_progress(self) -> bool:
        return (
            self._end_of_power_off is not None
            and self._end_of_power_off > dt_util.utcnow()
        )

    @property
    def available(self) -> bool:
        """Return the availability of the device."""
        if self._auth_failed:
            return False
        return (
            self._attr_state == STATE_ON
            or self._on_script is not None
            or self._mac is not None
            or self._power_off_in_progress()
        )

    async def async_turn_off(self) -> None:
        """Turn off media player."""
        self._end_of_power_off = dt_util.utcnow() + SCAN_INTERVAL_PLUS_OFF_TIME
        await self._bridge.async_power_off()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level on the media player."""
        if not (service := self._get_upnp_service(log=True)):
            return
        try:
            await service.action("SetVolume").async_call(
                InstanceID=0, Channel="Master", DesiredVolume=int(volume * 100)
            )
        except UpnpActionResponseError as err:
            LOGGER.warning(
                "Unable to set volume level on %s: %s", self._host, err.__repr__()
            )

    async def async_volume_up(self) -> None:
        """Volume up the media player."""
        await self._async_send_keys(["KEY_VOLUP"])

    async def async_volume_down(self) -> None:
        """Volume down media player."""
        await self._async_send_keys(["KEY_VOLDOWN"])

    async def async_mute_volume(self, mute: bool) -> None:
        """Send mute command."""
        await self._async_send_keys(["KEY_MUTE"])

    async def async_media_play_pause(self) -> None:
        """Simulate play pause media player."""
        if self._playing:
            await self.async_media_pause()
        else:
            await self.async_media_play()

    async def async_media_play(self) -> None:
        """Send play command."""
        self._playing = True
        await self._async_send_keys(["KEY_PLAY"])

    async def async_media_pause(self) -> None:
        """Send media pause command to media player."""
        self._playing = False
        await self._async_send_keys(["KEY_PAUSE"])

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self._async_send_keys(["KEY_CHUP"])

    async def async_media_previous_track(self) -> None:
        """Send the previous track command."""
        await self._async_send_keys(["KEY_CHDOWN"])

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        """Support changing a channel."""
        if media_type == MEDIA_TYPE_APP:
            await self._async_launch_app(media_id)
            return

        if media_type != MEDIA_TYPE_CHANNEL:
            LOGGER.error("Unsupported media type")
            return

        # media_id should only be a channel number
        try:
            cv.positive_int(media_id)
        except vol.Invalid:
            LOGGER.error("Media ID must be positive integer")
            return

        await self._async_send_keys(
            keys=[f"KEY_{digit}" for digit in media_id] + ["KEY_ENTER"]
        )

    def _wake_on_lan(self) -> None:
        """Wake the device via wake on lan."""
        send_magic_packet(self._mac, ip_address=self._host)
        # If the ip address changed since we last saw the device
        # broadcast a packet as well
        send_magic_packet(self._mac)

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        if self._on_script:
            await self._on_script.async_run(context=self._context)
        elif self._mac:
            await self.hass.async_add_executor_job(self._wake_on_lan)

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        if self._app_list and source in self._app_list:
            await self._async_launch_app(self._app_list[source])
            return

        if source in SOURCES:
            await self._async_send_keys([SOURCES[source]])
            return

        LOGGER.error("Unsupported source")
