"""Support for repeating alerts when conditions are met."""
from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import logging
from typing import Any, Self

import voluptuous as vol

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_MESSAGE,
    ATTR_TITLE,
    DOMAIN as DOMAIN_NOTIFY,
)
from homeassistant.const import (
    CONF_ENTITY_ID,
    CONF_ID,
    CONF_NAME,
    CONF_REPEAT,
    CONF_STATE,
    SERVICE_RELOAD,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_IDLE,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HassJob, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceNotFound
from homeassistant.helpers import collection
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_point_in_time,
    async_track_state_change_event,
)
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.storage import Store
from homeassistant.helpers.template import Template
from homeassistant.helpers.typing import ConfigType, EventType
from homeassistant.util.dt import now

from .const import (
    CONF_ALERT_MESSAGE,
    CONF_CAN_ACK,
    CONF_DATA,
    CONF_DONE_MESSAGE,
    CONF_NOTIFIERS,
    CONF_SKIP_FIRST,
    CONF_TITLE,
    DEFAULT_CAN_ACK,
    DEFAULT_SKIP_FIRST,
    DOMAIN,
    LOGGER,
)

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1
STORAGE_VERSION_MINOR = 0

STORAGE_FIELDS = {
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ENTITY_ID): cv.entity_id,
    vol.Optional(CONF_STATE, default=STATE_ON): cv.string,
    vol.Required(CONF_REPEAT): vol.All(
        cv.ensure_list,
        [vol.Coerce(float)],
        # Minimum delay is 1 second = 0.016 minutes
        [vol.Range(min=0.016)],
    ),
    vol.Optional(CONF_CAN_ACK, default=DEFAULT_CAN_ACK): cv.boolean,
    vol.Optional(CONF_SKIP_FIRST, default=DEFAULT_SKIP_FIRST): cv.boolean,
    vol.Optional(CONF_ALERT_MESSAGE): cv.template,
    vol.Optional(CONF_DONE_MESSAGE): cv.template,
    vol.Optional(CONF_TITLE): cv.template,
    vol.Optional(CONF_DATA): dict,
    vol.Optional(CONF_NOTIFIERS, default=list): vol.All(cv.ensure_list, [cv.string]),
}

ALERT_SCHEMA = vol.Schema(STORAGE_FIELDS)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: cv.schema_with_slug_keys(ALERT_SCHEMA)}, extra=vol.ALLOW_EXTRA
)
RELOAD_SERVICE_SCHEMA = vol.Schema({})


class AlertStore(Store):
    """Store entity registry data."""


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Alert component."""

    component = EntityComponent[Alert](LOGGER, DOMAIN, hass)

    id_manager = collection.IDManager()

    yaml_collection = collection.YamlCollection(
        logging.getLogger(f"{__name__}.yaml_collection"), id_manager
    )
    collection.sync_entity_lifecycle(
        hass, DOMAIN, DOMAIN, component, yaml_collection, Alert
    )

    storage_collection = AlertStorageCollection(
        AlertStore(
            hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_VERSION_MINOR
        ),
        id_manager,
    )
    collection.sync_entity_lifecycle(
        hass, DOMAIN, DOMAIN, component, storage_collection, Alert
    )

    await yaml_collection.async_load(
        [{CONF_ID: id_, **cfg} for id_, cfg in config[DOMAIN].items()]
    )
    await storage_collection.async_load()

    collection.DictStorageCollectionWebsocket(
        storage_collection, DOMAIN, DOMAIN, STORAGE_FIELDS, STORAGE_FIELDS
    ).async_setup(hass)

    async def reload_service_handler(_: ServiceCall) -> None:
        """Reload yaml entities."""
        conf = await component.async_prepare_reload(skip_reset=True) or {}
        await yaml_collection.async_load(
            [{CONF_ID: id_, **cfg} for id_, cfg in conf.get(DOMAIN, {}).items()]
        )

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RELOAD,
        reload_service_handler,
        schema=RELOAD_SERVICE_SCHEMA,
    )

    component.async_register_entity_service(SERVICE_TURN_OFF, {}, "async_turn_off")
    component.async_register_entity_service(SERVICE_TURN_ON, {}, "async_turn_on")
    component.async_register_entity_service(SERVICE_TOGGLE, {}, "async_toggle")

    return True


class AlertStorageCollection(collection.DictStorageCollection):
    """Input storage based collection."""

    CREATE_UPDATE_SCHEMA = ALERT_SCHEMA

    async def _process_create_data(self, data: dict[str, Any]) -> dict[str, Any]:  # type: ignore[empty-body]
        """Validate the config is valid."""

    @callback
    def _get_suggested_id(self, info: dict[str, Any]) -> str:  # type: ignore[empty-body]
        """Suggest an ID based on the config."""

    async def _update_data(  # type: ignore[empty-body]
        self, item: dict[str, Any], update_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Return a new updated data object."""


class Alert(collection.CollectionEntity):
    """Representation of an alert."""

    _attr_should_poll = False

    _alert_state: str
    _can_ack: bool
    _config: ConfigType
    _skip_first: bool
    _done_message_template: Template | None
    _title_template: Template | None
    _message_template: Template | None
    _data: dict[str, Any] | None

    def __init__(
        self,
        config: ConfigType,
    ) -> None:
        """Initialize the alert."""
        self._next_delay = 0

        self._firing = False
        self._ack = False
        self._cancel: Callable[[], None] | None = None
        self._send_done_message = False

        self._tracker: Callable[[], None] | None = None
        self._async_load_config(config)

    @callback
    def _async_load_config(self, config: ConfigType) -> None:
        """Load the alert config."""
        self._attr_name = config[CONF_NAME]
        self._alert_state = config[CONF_STATE]
        self._skip_first = config[CONF_SKIP_FIRST]
        self._data = config.get(CONF_DATA)

        self._message_template = config.get(CONF_ALERT_MESSAGE)
        self._done_message_template = config.get(CONF_DONE_MESSAGE)
        self._title_template = config.get(CONF_TITLE)

        self._notifiers = config[CONF_NOTIFIERS]
        self._can_ack = config[CONF_CAN_ACK]

        self._delay = [timedelta(minutes=val) for val in config[CONF_REPEAT]]
        self._config = config

    async def async_added_to_hass(self) -> None:
        """Initialize alert when the entity is loaded."""
        self._async_init_state_tracker()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up alert tracker when the entity is to be removed."""
        if self._tracker is not None:
            self._tracker()
            self._tracker = None

    async def async_update_config(self, config: ConfigType) -> None:
        """Handle when the config is loaded or updated."""
        self._async_load_config(config)
        self._async_init_state_tracker()

    @callback
    def _async_init_state_tracker(self) -> None:
        """Initialize state tracker and templates."""
        if self._tracker is not None:
            self._tracker()
            self._tracker = None
        self._tracker = async_track_state_change_event(
            self.hass, [self._config[CONF_ENTITY_ID]], self.watched_entity_change
        )
        if self._message_template is not None:
            self._message_template.hass = self.hass

        self._done_message_template = self._config.get(CONF_DONE_MESSAGE)
        if self._done_message_template is not None:
            self._done_message_template.hass = self.hass

        self._title_template = self._config.get(CONF_TITLE)
        if self._title_template is not None:
            self._title_template.hass = self.hass

    @classmethod
    def from_storage(cls, config: ConfigType) -> Self:  # type: ignore[empty-body]
        """Return entity instance initialized from storage."""

    @classmethod
    def from_yaml(cls, config: ConfigType) -> Self:
        """Return entity instance initialized from yaml."""
        alert = cls(config)
        alert.entity_id = f"{DOMAIN}.{config[CONF_ID]}"
        return alert

    @property
    def state(self) -> str:
        """Return the alert status."""
        if self._firing:
            if self._ack:
                return STATE_OFF
            return STATE_ON
        return STATE_IDLE

    async def watched_entity_change(
        self, event: EventType[EventStateChangedData]
    ) -> None:
        """Determine if the alert should start or stop."""
        if (to_state := event.data["new_state"]) is None:
            return
        LOGGER.debug("Watched entity (%s) has changed", event.data["entity_id"])
        if to_state.state == self._alert_state and not self._firing:
            await self.begin_alerting()
        if to_state.state != self._alert_state and self._firing:
            await self.end_alerting()

    async def begin_alerting(self) -> None:
        """Begin the alert procedures."""
        LOGGER.debug("Beginning Alert: %s", self._attr_name)
        self._ack = False
        self._firing = True
        self._next_delay = 0

        if not self._skip_first:
            await self._notify()
        else:
            await self._schedule_notify()

        self.async_write_ha_state()

    async def end_alerting(self) -> None:
        """End the alert procedures."""
        LOGGER.debug("Ending Alert: %s", self._attr_name)
        if self._cancel is not None:
            self._cancel()
            self._cancel = None

        self._ack = False
        self._firing = False
        if self._send_done_message:
            await self._notify_done_message()
        self.async_write_ha_state()

    async def _schedule_notify(self) -> None:
        """Schedule a notification."""
        delay = self._delay[self._next_delay]
        next_msg = now() + delay
        self._cancel = async_track_point_in_time(
            self.hass,
            HassJob(
                self._notify, name="Schedule notify alert", cancel_on_shutdown=True
            ),
            next_msg,
        )
        self._next_delay = min(self._next_delay + 1, len(self._delay) - 1)

    async def _notify(self, *args: Any) -> None:
        """Send the alert notification."""
        if not self._firing:
            return

        if not self._ack:
            LOGGER.info("Alerting: %s", self._attr_name)
            self._send_done_message = True

            if self._message_template is not None:
                message = self._message_template.async_render(parse_result=False)
            else:
                message = self._attr_name

            await self._send_notification_message(message)
        await self._schedule_notify()

    async def _notify_done_message(self) -> None:
        """Send notification of complete alert."""
        LOGGER.info("Alerting: %s", self._done_message_template)
        self._send_done_message = False

        if self._done_message_template is None:
            return

        message = self._done_message_template.async_render(parse_result=False)

        await self._send_notification_message(message)

    async def _send_notification_message(self, message: Any) -> None:
        if not self._notifiers:
            return

        msg_payload = {ATTR_MESSAGE: message}

        if self._title_template is not None:
            title = self._title_template.async_render(parse_result=False)
            msg_payload[ATTR_TITLE] = title
        if self._data:
            msg_payload[ATTR_DATA] = self._data

        LOGGER.debug(msg_payload)

        for target in self._notifiers:
            try:
                await self.hass.services.async_call(
                    DOMAIN_NOTIFY, target, msg_payload, context=self._context
                )
            except ServiceNotFound:
                LOGGER.error(
                    "Failed to call notify.%s, retrying at next notification interval",
                    target,
                )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Async Unacknowledge alert."""
        LOGGER.debug("Reset Alert: %s", self._attr_name)
        self._ack = False
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Async Acknowledge alert."""
        LOGGER.debug("Acknowledged Alert: %s", self._attr_name)
        self._ack = True
        self.async_write_ha_state()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Async toggle alert."""
        if self._ack:
            return await self.async_turn_on()
        return await self.async_turn_off()
