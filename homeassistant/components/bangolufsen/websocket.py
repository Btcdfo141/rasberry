"""Update coordinator and WebSocket listener(s) for the Bang & Olufsen integration."""
# pylint: disable=raise-missing-from

from __future__ import annotations

from datetime import datetime
import logging

from mozart_api.models import (
    PlaybackContentMetadata,
    PlaybackError,
    PlaybackProgress,
    RenderingState,
    SoftwareUpdateState,
    Source,
    VolumeState,
    WebsocketNotificationTag,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    BANGOLUFSEN_WEBSOCKET_EVENT,
    CONNECTION_STATUS,
    WEBSOCKET_NOTIFICATION,
)
from .entity import BangOlufsenVariables
from .util import get_device

_LOGGER = logging.getLogger(__name__)


class BangOlufsenWebsocket(BangOlufsenVariables):
    """The WebSocket listeners."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the WebSocket listeners."""

        BangOlufsenVariables.__init__(self, entry)

        self.hass = hass

        # WebSocket callbacks
        self._client.get_on_connection(self.on_connection)
        self._client.get_on_connection_lost(self.on_connection_lost)
        self._client.get_notification_notifications(self.on_notification_notification)
        self._client.get_playback_error_notifications(
            self.on_playback_error_notification
        )
        self._client.get_playback_metadata_notifications(
            self.on_playback_metadata_notification
        )
        self._client.get_playback_progress_notifications(
            self.on_playback_progress_notification
        )
        self._client.get_playback_state_notifications(
            self.on_playback_state_notification
        )
        self._client.get_source_change_notifications(self.on_source_change_notification)
        self._client.get_volume_notifications(self.on_volume_notification)
        self._client.get_software_update_state_notifications(
            self.on_software_update_state
        )

        # Used for firing events and debugging
        self._client.get_all_notifications_raw(self.on_all_notifications_raw)

    def connect_websocket(self, _: datetime | None = None) -> None:
        """Start the notification WebSocket listeners."""
        if self._client.websocket_connected:
            return

        self._client.connect_notifications(remote_control=True)

    def disconnect(self) -> None:
        """Terminate the WebSocket connections and remove dispatchers."""
        self._client.disconnect_notifications()
        self._update_connection_status()

    def _update_connection_status(self) -> None:
        """Update all entities of the connection status."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{CONNECTION_STATUS}",
            self._client.websocket_connected,
        )

    def on_connection(self) -> None:
        """Handle WebSocket connection made."""
        _LOGGER.debug("Connected to the %s notification channel", self._name)
        self._update_connection_status()

    def on_connection_lost(self) -> None:
        """Handle WebSocket connection lost."""
        _LOGGER.error("Lost connection to the %s", self._name)
        self._update_connection_status()

    def on_notification_notification(
        self, notification: WebsocketNotificationTag
    ) -> None:
        """Send notification dispatch."""
        if notification.value:
            if WEBSOCKET_NOTIFICATION.REMOTE_MENU_CHANGED in notification.value:
                async_dispatcher_send(
                    self.hass,
                    f"{self._unique_id}_{WEBSOCKET_NOTIFICATION.REMOTE_MENU_CHANGED}",
                )

    def on_playback_error_notification(self, notification: PlaybackError) -> None:
        """Send playback_error dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WEBSOCKET_NOTIFICATION.PLAYBACK_ERROR}",
            notification,
        )

    def on_playback_metadata_notification(
        self, notification: PlaybackContentMetadata
    ) -> None:
        """Send playback_metadata dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WEBSOCKET_NOTIFICATION.PLAYBACK_METADATA}",
            notification,
        )

    def on_playback_progress_notification(self, notification: PlaybackProgress) -> None:
        """Send playback_progress dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WEBSOCKET_NOTIFICATION.PLAYBACK_PROGRESS}",
            notification,
        )

    def on_playback_state_notification(self, notification: RenderingState) -> None:
        """Send playback_state dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WEBSOCKET_NOTIFICATION.PLAYBACK_STATE}",
            notification,
        )

    def on_source_change_notification(self, notification: Source) -> None:
        """Send source_change dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WEBSOCKET_NOTIFICATION.SOURCE_CHANGE}",
            notification,
        )

    def on_volume_notification(self, notification: VolumeState) -> None:
        """Send volume dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WEBSOCKET_NOTIFICATION.VOLUME}",
            notification,
        )

    def on_software_update_state(self, notification: SoftwareUpdateState) -> None:
        """Send software_update_state dispatch."""
        async_dispatcher_send(
            self.hass,
            f"{self._unique_id}_{WEBSOCKET_NOTIFICATION.SOFTWARE_UPDATE_STATE}",
            notification,
        )

    def on_all_notifications_raw(self, notification: dict) -> None:
        """Receive all notifications."""
        if not isinstance(self._device, DeviceEntry):
            self._device = get_device(self.hass, self._unique_id)

        assert isinstance(self._device, DeviceEntry)

        # Add the device_id and serial_number to the notification
        notification["device_id"] = self._device.id
        notification["serial_number"] = int(self._unique_id)

        _LOGGER.debug("%s", notification)
        self.hass.bus.async_fire(BANGOLUFSEN_WEBSOCKET_EVENT, notification)
