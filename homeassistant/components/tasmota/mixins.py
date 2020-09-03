"""Tasnmota entity mixins."""
import logging

from hatasmota.const import CONF_AVAILABILITY_TOPIC, CONF_OFFLINE, CONF_ONLINE, CONF_QOS

from homeassistant.components.mqtt.const import MQTT_CONNECTED, MQTT_DISCONNECTED
from homeassistant.components.mqtt.debug_info import log_messages
from homeassistant.components.mqtt.models import Message
from homeassistant.components.mqtt.subscription import (
    async_subscribe_topics,
    async_unsubscribe_topics,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .discovery import TASMOTA_DISCOVERY_ENTITY_UPDATED, clear_discovery_hash

DATA_MQTT = "mqtt"

_LOGGER = logging.getLogger(__name__)


class TasmotaAvailability(Entity):
    """Mixin used for platforms that report availability."""

    def __init__(self, config: dict) -> None:
        """Initialize the availability mixin."""
        self._availability_sub_state = None
        self._available = False
        self._availability_setup_from_config(config)

    async def async_added_to_hass(self) -> None:
        """Subscribe MQTT events."""
        await super().async_added_to_hass()
        await self._availability_subscribe_topics()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, MQTT_CONNECTED, self.async_mqtt_connect)
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, MQTT_DISCONNECTED, self.async_mqtt_connect
            )
        )

    async def availability_discovery_update(self, config: dict):
        """Handle updated discovery message."""
        self._availability_setup_from_config(config)
        await self._availability_subscribe_topics()

    def _availability_setup_from_config(self, config):
        """(Re)Setup."""
        self._avail_config = config

    async def _availability_subscribe_topics(self):
        """(Re)Subscribe to topics."""

        @callback
        @log_messages(self.hass, self.entity_id)
        def availability_message_received(msg: Message) -> None:
            """Handle a new received MQTT availability message."""
            if msg.payload == self._avail_config[CONF_ONLINE]:
                self._available = True
            if msg.payload == self._avail_config[CONF_OFFLINE]:
                self._available = False

            self.async_write_ha_state()

        availability_topic = self._avail_config[CONF_AVAILABILITY_TOPIC]
        self._availability_sub_state = await async_subscribe_topics(
            self.hass,
            self._availability_sub_state,
            {
                "availability_topic": {
                    "topic": availability_topic,
                    "msg_callback": availability_message_received,
                    "qos": self._avail_config[CONF_QOS],
                }
            },
        )

    @callback
    def async_mqtt_connect(self):
        """Update state on connection/disconnection to MQTT broker."""
        if not self.hass.is_stopping:
            self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._availability_sub_state = await async_unsubscribe_topics(
            self.hass, self._availability_sub_state
        )

    @property
    def available(self) -> bool:
        """Return if the device is available."""
        if not self.hass.data[DATA_MQTT].connected and not self.hass.is_stopping:
            return False
        return self._available


class TasmotaDiscoveryUpdate(Entity):
    """Mixin used to handle updated discovery message."""

    def __init__(self, config, discovery_hash, discovery_update) -> None:
        """Initialize the discovery update mixin."""
        self._discovery_config = config
        self._discovery_hash = discovery_hash
        self._discovery_update = discovery_update
        self._remove_signal = None
        self._removed_from_hass = False

    async def async_added_to_hass(self) -> None:
        """Subscribe to discovery updates."""
        await super().async_added_to_hass()
        self._removed_from_hass = False

        @callback
        async def discovery_callback(config):
            """Handle discovery update."""
            _LOGGER.info(
                "Got update for entity with hash: %s '%s'",
                self._discovery_hash,
                config,
            )
            old_config = self._discovery_config
            self._discovery_config = config
            if old_config != config:
                # Changed payload: Notify component
                _LOGGER.info("Updating component: %s", self.entity_id)
                await self._discovery_update(config)
            else:
                # Unchanged payload: Ignore to avoid changing states
                _LOGGER.info("Ignoring unchanged update for: %s", self.entity_id)

        # Set in case the entity has been removed and is re-added
        self._remove_signal = async_dispatcher_connect(
            self.hass,
            TASMOTA_DISCOVERY_ENTITY_UPDATED.format(*self._discovery_hash),
            discovery_callback,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Stop listening to signal and cleanup discovery data.."""
        self._cleanup_discovery_on_remove()

    def _cleanup_discovery_on_remove(self) -> None:
        """Stop listening to signal and cleanup discovery data."""
        if self._discovery_config and not self._removed_from_hass:
            clear_discovery_hash(self.hass, self._discovery_hash)
            self._removed_from_hass = True

        if self._remove_signal:
            self._remove_signal()
            self._remove_signal = None
