"""A sensor for incoming calls using a USB modem that supports caller ID."""
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (
    CONF_DEVICE,
    CONF_NAME,
    EVENT_HOMEASSISTANT_STOP,
    STATE_IDLE,
)
from homeassistant.helpers import config_validation as cv, entity_platform

from .const import (
    DATA_KEY_API,
    DEFAULT_DEVICE,
    DEFAULT_NAME,
    DOMAIN,
    ICON,
    SERVICE_REJECT_CALL,
    STATE_CALLERID,
    STATE_RING,
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE, default=DEFAULT_DEVICE): cv.string,
    }
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Modem Caller ID sensor."""
    name = entry.data[CONF_NAME]
    device = entry.data[CONF_DEVICE]
    api = hass.data[DOMAIN][entry.entry_id][DATA_KEY_API]
    async_add_entities(
        [
            ModemCalleridSensor(
                hass,
                api,
                name,
                device,
                entry.entry_id,
            )
        ]
    )

    async def on_hass_stop(self, event):
        """HA is shutting down, close modem port."""
        if self.api:
            self.api.close()
            self.api = None

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, on_hass_stop)
    )

    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(SERVICE_REJECT_CALL, {}, "reject_call")


class ModemCalleridSensor(SensorEntity):
    """Implementation of USB modem caller ID sensor."""

    def __init__(self, hass, api, name, device, server_unique_id):
        """Initialize the sensor."""
        self._attributes = {"cid_time": 0, "cid_number": "", "cid_name": ""}
        self._device_class = None
        self.device = device
        self.api = api
        self._state = STATE_IDLE
        self._name = name
        self._server_unique_id = server_unique_id

    async def async_added_to_hass(self):
        """Call when the modem sensor is added to Home Assistant."""
        self.api.registercallback(self._incomingcallcallback)
        await super().async_added_to_hass()

    def set_state(self, state):
        """Set the state."""
        self._state = state

    def set_attributes(self, attributes):
        """Set the state attributes."""
        self._attributes = attributes

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def icon(self):
        """Return icon."""
        return ICON

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        return f"{self._server_unique_id}_modem"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def _incomingcallcallback(self, newstate):
        """Handle new states."""
        if newstate == self.api.STATE_RING:
            if self.state == self.api.STATE_IDLE:
                att = {
                    "cid_time": self.api.get_cidtime,
                    "cid_number": "",
                    "cid_name": "",
                }
                self.set_attributes(att)
            self._state = STATE_RING
            self.schedule_update_ha_state()
        elif newstate == self.api.STATE_CALLERID:
            att = {
                "cid_time": self.api.get_cidtime,
                "cid_number": self.api.get_cidnumber,
                "cid_name": self.api.get_cidname,
            }
            self.set_attributes(att)
            self._state = STATE_CALLERID
            self.schedule_update_ha_state()
        elif newstate == self.api.STATE_IDLE:
            self._state = STATE_IDLE
            self.schedule_update_ha_state()

    def reject_call(self) -> None:
        """Reject Incoming Call."""
        self.api.reject_call(self.device)
