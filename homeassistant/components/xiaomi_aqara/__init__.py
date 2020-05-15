"""Support for Xiaomi Gateways."""
from datetime import timedelta
import logging

import voluptuous as vol
from xiaomi_gateway import XiaomiGateway

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_VOLTAGE,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant import config_entries, core
from homeassistant.core import callback
from homeassistant.helpers import discovery, device_registry as dr
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util.dt import utcnow

from .config_flow import (
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

GATEWAY_PLATFORMS = ["binary_sensor", "sensor", "switch", "light", "cover", "lock"]

ATTR_GW_MAC = "gw_mac"
ATTR_RINGTONE_ID = "ringtone_id"
ATTR_RINGTONE_VOL = "ringtone_vol"
ATTR_DEVICE_ID = "device_id"

PY_XIAOMI_GATEWAY = "xiaomi_gw"

TIME_TILL_UNAVAILABLE = timedelta(minutes=150)

SERVICE_PLAY_RINGTONE = "play_ringtone"
SERVICE_STOP_RINGTONE = "stop_ringtone"
SERVICE_ADD_DEVICE = "add_device"
SERVICE_REMOVE_DEVICE = "remove_device"

SERVICE_SCHEMA_PLAY_RINGTONE = vol.Schema(
    {
        vol.Required(ATTR_RINGTONE_ID): vol.All(
            vol.Coerce(int), vol.NotIn([9, 14, 15, 16, 17, 18, 19])
        ),
        vol.Optional(ATTR_RINGTONE_VOL): vol.All(
            vol.Coerce(int), vol.Clamp(min=0, max=100)
        ),
    }
)

SERVICE_SCHEMA_REMOVE_DEVICE = vol.Schema(
    {vol.Required(ATTR_DEVICE_ID): vol.All(cv.string, vol.Length(min=14, max=14))}
)

def setup(hass, config):
    """Set up the Xiaomi component."""

    def play_ringtone_service(call):
        """Service to play ringtone through Gateway."""
        ring_id = call.data.get(ATTR_RINGTONE_ID)
        gateway = call.data.get(ATTR_GW_MAC)

        kwargs = {"mid": ring_id}

        ring_vol = call.data.get(ATTR_RINGTONE_VOL)
        if ring_vol is not None:
            kwargs["vol"] = ring_vol

        gateway.write_to_hub(gateway.sid, **kwargs)

    def stop_ringtone_service(call):
        """Service to stop playing ringtone on Gateway."""
        gateway = call.data.get(ATTR_GW_MAC)
        gateway.write_to_hub(gateway.sid, mid=10000)

    def add_device_service(call):
        """Service to add a new sub-device within the next 30 seconds."""
        gateway = call.data.get(ATTR_GW_MAC)
        gateway.write_to_hub(gateway.sid, join_permission="yes")
        hass.components.persistent_notification.async_create(
            "Join permission enabled for 30 seconds! "
            "Please press the pairing button of the new device once.",
            title="Xiaomi Aqara Gateway",
        )

    def remove_device_service(call):
        """Service to remove a sub-device from the gateway."""
        device_id = call.data.get(ATTR_DEVICE_ID)
        gateway = call.data.get(ATTR_GW_MAC)
        gateway.write_to_hub(gateway.sid, remove_device=device_id)

    gateway_only_schema = _add_gateway_to_schema(xiaomi, vol.Schema({}))

    hass.services.register(
        DOMAIN,
        SERVICE_PLAY_RINGTONE,
        play_ringtone_service,
        schema=_add_gateway_to_schema(xiaomi, SERVICE_SCHEMA_PLAY_RINGTONE),
    )

    hass.services.register(
        DOMAIN, SERVICE_STOP_RINGTONE, stop_ringtone_service, schema=gateway_only_schema
    )

    hass.services.register(
        DOMAIN, SERVICE_ADD_DEVICE, add_device_service, schema=gateway_only_schema
    )

    hass.services.register(
        DOMAIN,
        SERVICE_REMOVE_DEVICE,
        remove_device_service,
        schema=_add_gateway_to_schema(xiaomi, SERVICE_SCHEMA_REMOVE_DEVICE),
    )

    return True


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
):
    """Set up the xiaomi aqara components from a config entry."""
    if hass.data[DOMAIN] is None:
        hass.data[DOMAIN] = {}

    # Connect to Xiaomi Aqara Gateway
    xiaomi_gateway = XiaomiGateway(entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_SID], entry.data[CONF_KEY], entry.data[CONF_DISCOVERY_RETRY], entry.data[CONF_INTERFACE], proto=entry.data[CONF_PROTOCOL])
    hass.data[DOMAIN][entry.entry_id] = xiaomi_gateway

    # start listining for local pushes
    xiaomi_gateway.listen()
    _LOGGER.debug("Gateway with host '%s' connected, listening for broadcasts", entry.data[CONF_HOST])

    # register stop callback to shutdown listining for local pushes
    def stop_xiaomi(event):
        """Stop Xiaomi Socket."""
        _LOGGER.info("Shutting down Xiaomi Gateway")
        xiaomi_gateway.stop_listen()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_xiaomi)
    
    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, entry.data[CONF_MAC])},
        identifiers={(DOMAIN, entry.unique_id)},
        manufacturer="Xiaomi Aqara",
        name=entry.title,
        sw_version=entry.data[CONF_PROTOCOL],
    )

    for component in GATEWAY_PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


class XiaomiDevice(Entity):
    """Representation a base Xiaomi device."""

    def __init__(self, device, device_type, xiaomi_hub):
        """Initialize the Xiaomi device."""
        self._state = None
        self._is_available = True
        self._sid = device["sid"]
        self._name = f"{device_type}_{self._sid}"
        self._type = device_type
        self._write_to_hub = xiaomi_hub.write_to_hub
        self._get_from_hub = xiaomi_hub.get_from_hub
        self._device_state_attributes = {}
        self._remove_unavailability_tracker = None
        self._xiaomi_hub = xiaomi_hub
        self.parse_data(device["data"], device["raw_data"])
        self.parse_voltage(device["data"])

        if hasattr(self, "_data_key") and self._data_key:  # pylint: disable=no-member
            self._unique_id = (
                f"{self._data_key}{self._sid}"  # pylint: disable=no-member
            )
        else:
            self._unique_id = f"{self._type}{self._sid}"

    def _add_push_data_job(self, *args):
        self.hass.add_job(self.push_data, *args)

    async def async_added_to_hass(self):
        """Start unavailability tracking."""
        self._xiaomi_hub.callbacks[self._sid].append(self._add_push_data_job)
        self._async_track_unavailable()

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def available(self):
        """Return True if entity is available."""
        return self._is_available

    @property
    def should_poll(self):
        """Return the polling state. No polling needed."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._device_state_attributes

    @callback
    def _async_set_unavailable(self, now):
        """Set state to UNAVAILABLE."""
        self._remove_unavailability_tracker = None
        self._is_available = False
        self.async_write_ha_state()

    @callback
    def _async_track_unavailable(self):
        if self._remove_unavailability_tracker:
            self._remove_unavailability_tracker()
        self._remove_unavailability_tracker = async_track_point_in_utc_time(
            self.hass, self._async_set_unavailable, utcnow() + TIME_TILL_UNAVAILABLE
        )
        if not self._is_available:
            self._is_available = True
            return True
        return False

    @callback
    def push_data(self, data, raw_data):
        """Push from Hub."""
        _LOGGER.debug("PUSH >> %s: %s", self, data)
        was_unavailable = self._async_track_unavailable()
        is_data = self.parse_data(data, raw_data)
        is_voltage = self.parse_voltage(data)
        if is_data or is_voltage or was_unavailable:
            self.async_write_ha_state()

    def parse_voltage(self, data):
        """Parse battery level data sent by gateway."""
        if "voltage" in data:
            voltage_key = "voltage"
        elif "battery_voltage" in data:
            voltage_key = "battery_voltage"
        else:
            return False

        max_volt = 3300
        min_volt = 2800
        voltage = data[voltage_key]
        self._device_state_attributes[ATTR_VOLTAGE] = round(voltage / 1000.0, 2)
        voltage = min(voltage, max_volt)
        voltage = max(voltage, min_volt)
        percent = ((voltage - min_volt) / (max_volt - min_volt)) * 100
        self._device_state_attributes[ATTR_BATTERY_LEVEL] = round(percent, 1)
        return True

    def parse_data(self, data, raw_data):
        """Parse data sent by gateway."""
        raise NotImplementedError()


def _add_gateway_to_schema(xiaomi, schema):
    """Extend a voluptuous schema with a gateway validator."""

    def gateway(sid):
        """Convert sid to a gateway."""
        sid = str(sid).replace(":", "").lower()

        for gateway in xiaomi.gateways.values():
            if gateway.sid == sid:
                return gateway

        raise vol.Invalid(f"Unknown gateway sid {sid}")

    gateways = list(xiaomi.gateways.values())
    kwargs = {}

    # If the user has only 1 gateway, make it the default for services.
    if len(gateways) == 1:
        kwargs["default"] = gateways[0].sid

    return schema.extend({vol.Required(ATTR_GW_MAC, **kwargs): gateway})
