"""Extend the basic Accessory and Bridge functions."""
import logging

from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_OTHER
from pyhap.util import callback as pyhap_callback

from homeassistant.components import cover
from homeassistant.components.climate.const import SUPPORT_FAN_MODE, SUPPORT_SWING_MODE
from homeassistant.components.media_player import MediaPlayerDeviceClass
from homeassistant.components.remote import SUPPORT_ACTIVITY
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_BATTERY_CHARGING,
    ATTR_BATTERY_LEVEL,
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_HW_VERSION,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_SERVICE,
    ATTR_SUPPORTED_FEATURES,
    ATTR_SW_VERSION,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_NAME,
    CONF_TYPE,
    LIGHT_LUX,
    PERCENTAGE,
    STATE_ON,
    STATE_UNAVAILABLE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    __version__,
)
from homeassistant.core import Context, callback as ha_callback, split_entity_id
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util.decorator import Registry

from .const import (
    ATTR_DISPLAY_NAME,
    ATTR_INTEGRATION,
    ATTR_VALUE,
    BRIDGE_MODEL,
    BRIDGE_SERIAL_NUMBER,
    CHAR_BATTERY_LEVEL,
    CHAR_CHARGING_STATE,
    CHAR_HARDWARE_REVISION,
    CHAR_STATUS_LOW_BATTERY,
    CONF_FEATURE_LIST,
    CONF_LINKED_BATTERY_CHARGING_SENSOR,
    CONF_LINKED_BATTERY_SENSOR,
    CONF_LOW_BATTERY_THRESHOLD,
    DEFAULT_LOW_BATTERY_THRESHOLD,
    DOMAIN,
    EVENT_HOMEKIT_CHANGED,
    HK_CHARGING,
    HK_NOT_CHARGABLE,
    HK_NOT_CHARGING,
    MANUFACTURER,
    MAX_MANUFACTURER_LENGTH,
    MAX_MODEL_LENGTH,
    MAX_SERIAL_LENGTH,
    MAX_VERSION_LENGTH,
    SERV_ACCESSORY_INFO,
    SERV_BATTERY_SERVICE,
    SERVICE_HOMEKIT_RESET_ACCESSORY,
    TYPE_FAUCET,
    TYPE_OUTLET,
    TYPE_SHOWER,
    TYPE_SPRINKLER,
    TYPE_SWITCH,
    TYPE_VALVE,
)
from .util import (
    accessory_friendly_name,
    async_dismiss_setup_message,
    async_show_setup_message,
    cleanup_name_for_homekit,
    convert_to_float,
    format_version,
    validate_media_player_features,
)

_LOGGER = logging.getLogger(__name__)
SWITCH_TYPES = {
    TYPE_FAUCET: "Valve",
    TYPE_OUTLET: "Outlet",
    TYPE_SHOWER: "Valve",
    TYPE_SPRINKLER: "Valve",
    TYPE_SWITCH: "Switch",
    TYPE_VALVE: "Valve",
}
TYPES = Registry()


def get_accessories(hass, driver, state, aid, config, aid_storage=None):  # noqa: C901
    """Take state and return an accessory object if supported."""
    a_types = []
    name = config.get(CONF_NAME, state.name)
    entity_id = state.entity_id
    features = state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

    if state.domain == "alarm_control_panel":
        a_types.append("SecuritySystem")

    elif state.domain in ("binary_sensor", "device_tracker", "person"):
        a_types.append("BinarySensor")

    elif state.domain == "climate":
        a_types.append("Thermostat")
        if features & SUPPORT_FAN_MODE:
            a_types.append("ThermostatFanMode")
        if features & SUPPORT_SWING_MODE:
            a_types.append("ThermostatSwingMode")

    elif state.domain == "cover":
        device_class = state.attributes.get(ATTR_DEVICE_CLASS)

        if device_class in (
            cover.CoverDeviceClass.GARAGE,
            cover.CoverDeviceClass.GATE,
        ) and features & (cover.SUPPORT_OPEN | cover.SUPPORT_CLOSE):
            a_types.append("GarageDoorOpener")
        elif (
            device_class == cover.CoverDeviceClass.WINDOW
            and features & cover.SUPPORT_SET_POSITION
        ):
            a_types.append("Window")
        elif features & cover.SUPPORT_SET_POSITION:
            a_types.append("WindowCovering")
        elif features & (cover.SUPPORT_OPEN | cover.SUPPORT_CLOSE):
            a_types.append("WindowCoveringBasic")
        elif features & cover.SUPPORT_SET_TILT_POSITION:
            # WindowCovering and WindowCoveringBasic both support tilt
            # only WindowCovering can handle the covers that are missing
            # SUPPORT_SET_POSITION, SUPPORT_OPEN, and SUPPORT_CLOSE
            a_types.append("WindowCovering")

    elif state.domain == "fan":
        a_types.append("Fan")

    elif state.domain == "humidifier":
        a_types.append("HumidifierDehumidifier")

    elif state.domain == "light":
        a_types.append("Light")

    elif state.domain == "lock":
        a_types.append("Lock")

    elif state.domain == "media_player":
        device_class = state.attributes.get(ATTR_DEVICE_CLASS)
        feature_list = config.get(CONF_FEATURE_LIST, [])

        if device_class == MediaPlayerDeviceClass.TV:
            a_types.append("TelevisionMediaPlayer")
        elif validate_media_player_features(state, feature_list):
            a_types.append("MediaPlayer")

    elif state.domain == "sensor":
        device_class = state.attributes.get(ATTR_DEVICE_CLASS)
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

        if device_class == SensorDeviceClass.TEMPERATURE or unit in (
            TEMP_CELSIUS,
            TEMP_FAHRENHEIT,
        ):
            a_types.append("TemperatureSensor")
        elif device_class == SensorDeviceClass.HUMIDITY and unit == PERCENTAGE:
            a_types.append("HumiditySensor")
        elif (
            device_class == SensorDeviceClass.PM25
            or SensorDeviceClass.PM25 in state.entity_id
        ):
            a_types.append("AirQualitySensor")
        elif device_class == SensorDeviceClass.CO:
            a_types.append("CarbonMonoxideSensor")
        elif device_class == SensorDeviceClass.CO2 or "co2" in state.entity_id:
            a_types.append("CarbonDioxideSensor")
        elif device_class == SensorDeviceClass.ILLUMINANCE or unit in ("lm", LIGHT_LUX):
            a_types.append("LightSensor")

    elif state.domain == "switch":
        switch_type = config.get(CONF_TYPE, TYPE_SWITCH)
        a_types.append(SWITCH_TYPES[switch_type])

    elif state.domain == "vacuum":
        a_types.append("Vacuum")

    elif state.domain == "remote" and features & SUPPORT_ACTIVITY:
        a_types.append("ActivityRemote")

    elif state.domain in (
        "automation",
        "button",
        "input_boolean",
        "input_button",
        "remote",
        "scene",
        "script",
    ):
        a_types.append("Switch")

    elif state.domain in ("input_select", "select"):
        a_types.append("SelectSwitch")

    elif state.domain == "water_heater":
        a_types.append("WaterHeater")

    elif state.domain == "camera":
        a_types.append("Camera")

    accessories = []
    for idx, a_type in enumerate(a_types):
        _LOGGER.debug('Add "%s" as "%s"', state.entity_id, a_type)
        # If the entity creates multiple accessories
        # we need to augment the air storage generator
        aid_trailer = f".{a_type}" if idx else None
        if aid is None:
            aid = aid_storage.get_or_allocate_aid_for_entity_id(entity_id, aid_trailer)
        accessories.append(
            TYPES[a_type](hass, driver, name, state.entity_id, aid, config)
        )

    return accessories


class HomeAccessory(Accessory):
    """Adapter class for Accessory."""

    def __init__(
        self,
        hass,
        driver,
        name,
        entity_id,
        aid,
        config,
        *args,
        category=CATEGORY_OTHER,
        device_id=None,
        **kwargs,
    ):
        """Initialize a Accessory object."""
        super().__init__(
            driver=driver,
            display_name=cleanup_name_for_homekit(name),
            aid=aid,
            *args,
            **kwargs,
        )
        self.config = config or {}
        if device_id:
            self.device_id = device_id
            serial_number = device_id
            domain = None
        else:
            self.device_id = None
            serial_number = entity_id
            domain = split_entity_id(entity_id)[0].replace("_", " ")

        if self.config.get(ATTR_MANUFACTURER) is not None:
            manufacturer = str(self.config[ATTR_MANUFACTURER])
        elif self.config.get(ATTR_INTEGRATION) is not None:
            manufacturer = self.config[ATTR_INTEGRATION].replace("_", " ").title()
        elif domain:
            manufacturer = f"{MANUFACTURER} {domain}".title()
        else:
            manufacturer = MANUFACTURER
        if self.config.get(ATTR_MODEL) is not None:
            model = str(self.config[ATTR_MODEL])
        elif domain:
            model = domain.title()
        else:
            model = MANUFACTURER
        sw_version = None
        if self.config.get(ATTR_SW_VERSION) is not None:
            sw_version = format_version(self.config[ATTR_SW_VERSION])
        if sw_version is None:
            sw_version = __version__
        hw_version = None
        if self.config.get(ATTR_HW_VERSION) is not None:
            hw_version = format_version(self.config[ATTR_HW_VERSION])

        self.set_info_service(
            manufacturer=manufacturer[:MAX_MANUFACTURER_LENGTH],
            model=model[:MAX_MODEL_LENGTH],
            serial_number=serial_number[:MAX_SERIAL_LENGTH],
            firmware_revision=sw_version[:MAX_VERSION_LENGTH],
        )
        if hw_version:
            serv_info = self.get_service(SERV_ACCESSORY_INFO)
            char = self.driver.loader.get_char(CHAR_HARDWARE_REVISION)
            serv_info.add_characteristic(char)
            serv_info.configure_char(CHAR_HARDWARE_REVISION, value=hw_version)
            self.iid_manager.assign(char)
            char.broker = self

        self.category = category
        self.entity_id = entity_id
        self.hass = hass
        self._subscriptions = []

        if device_id:
            return

        self._char_battery = None
        self._char_charging = None
        self._char_low_battery = None
        self.linked_battery_sensor = self.config.get(CONF_LINKED_BATTERY_SENSOR)
        self.linked_battery_charging_sensor = self.config.get(
            CONF_LINKED_BATTERY_CHARGING_SENSOR
        )
        self.low_battery_threshold = self.config.get(
            CONF_LOW_BATTERY_THRESHOLD, DEFAULT_LOW_BATTERY_THRESHOLD
        )

        """Add battery service if available"""
        entity_attributes = self.hass.states.get(self.entity_id).attributes
        battery_found = entity_attributes.get(ATTR_BATTERY_LEVEL)

        if self.linked_battery_sensor:
            state = self.hass.states.get(self.linked_battery_sensor)
            if state is not None:
                battery_found = state.state
            else:
                self.linked_battery_sensor = None
                _LOGGER.warning(
                    "%s: Battery sensor state missing: %s",
                    self.entity_id,
                    self.linked_battery_sensor,
                )

        if not battery_found:
            return

        _LOGGER.debug("%s: Found battery level", self.entity_id)

        if self.linked_battery_charging_sensor:
            state = self.hass.states.get(self.linked_battery_charging_sensor)
            if state is None:
                self.linked_battery_charging_sensor = None
                _LOGGER.warning(
                    "%s: Battery charging binary_sensor state missing: %s",
                    self.entity_id,
                    self.linked_battery_charging_sensor,
                )
            else:
                _LOGGER.debug("%s: Found battery charging", self.entity_id)

        serv_battery = self.add_preload_service(SERV_BATTERY_SERVICE)
        self._char_battery = serv_battery.configure_char(CHAR_BATTERY_LEVEL, value=0)
        self._char_charging = serv_battery.configure_char(
            CHAR_CHARGING_STATE, value=HK_NOT_CHARGABLE
        )
        self._char_low_battery = serv_battery.configure_char(
            CHAR_STATUS_LOW_BATTERY, value=0
        )

    @property
    def available(self):
        """Return if accessory is available."""
        state = self.hass.states.get(self.entity_id)
        return state is not None and state.state != STATE_UNAVAILABLE

    async def run(self):
        """Handle accessory driver started event."""
        state = self.hass.states.get(self.entity_id)
        self.async_update_state_callback(state)
        self._subscriptions.append(
            async_track_state_change_event(
                self.hass, [self.entity_id], self.async_update_event_state_callback
            )
        )

        battery_charging_state = None
        battery_state = None
        if self.linked_battery_sensor:
            linked_battery_sensor_state = self.hass.states.get(
                self.linked_battery_sensor
            )
            battery_state = linked_battery_sensor_state.state
            battery_charging_state = linked_battery_sensor_state.attributes.get(
                ATTR_BATTERY_CHARGING
            )
            self._subscriptions.append(
                async_track_state_change_event(
                    self.hass,
                    [self.linked_battery_sensor],
                    self.async_update_linked_battery_callback,
                )
            )
        elif state is not None:
            battery_state = state.attributes.get(ATTR_BATTERY_LEVEL)
        if self.linked_battery_charging_sensor:
            state = self.hass.states.get(self.linked_battery_charging_sensor)
            battery_charging_state = state and state.state == STATE_ON
            self._subscriptions.append(
                async_track_state_change_event(
                    self.hass,
                    [self.linked_battery_charging_sensor],
                    self.async_update_linked_battery_charging_callback,
                )
            )
        elif battery_charging_state is None and state is not None:
            battery_charging_state = state.attributes.get(ATTR_BATTERY_CHARGING)

        if battery_state is not None or battery_charging_state is not None:
            self.async_update_battery(battery_state, battery_charging_state)

    @ha_callback
    def async_update_event_state_callback(self, event):
        """Handle state change event listener callback."""
        self.async_update_state_callback(event.data.get("new_state"))

    @ha_callback
    def async_update_state_callback(self, new_state):
        """Handle state change listener callback."""
        _LOGGER.debug("New_state: %s", new_state)
        if new_state is None:
            return
        battery_state = None
        battery_charging_state = None
        if (
            not self.linked_battery_sensor
            and ATTR_BATTERY_LEVEL in new_state.attributes
        ):
            battery_state = new_state.attributes.get(ATTR_BATTERY_LEVEL)
        if (
            not self.linked_battery_charging_sensor
            and ATTR_BATTERY_CHARGING in new_state.attributes
        ):
            battery_charging_state = new_state.attributes.get(ATTR_BATTERY_CHARGING)
        if battery_state is not None or battery_charging_state is not None:
            self.async_update_battery(battery_state, battery_charging_state)
        self.async_update_state(new_state)

    @ha_callback
    def async_update_linked_battery_callback(self, event):
        """Handle linked battery sensor state change listener callback."""
        if (new_state := event.data.get("new_state")) is None:
            return
        if self.linked_battery_charging_sensor:
            battery_charging_state = None
        else:
            battery_charging_state = new_state.attributes.get(ATTR_BATTERY_CHARGING)
        self.async_update_battery(new_state.state, battery_charging_state)

    @ha_callback
    def async_update_linked_battery_charging_callback(self, event):
        """Handle linked battery charging sensor state change listener callback."""
        if (new_state := event.data.get("new_state")) is None:
            return
        self.async_update_battery(None, new_state.state == STATE_ON)

    @ha_callback
    def async_update_battery(self, battery_level, battery_charging):
        """Update battery service if available.

        Only call this function if self._support_battery_level is True.
        """
        if not self._char_battery:
            # Battery appeared after homekit was started
            return

        battery_level = convert_to_float(battery_level)
        if battery_level is not None:
            if self._char_battery.value != battery_level:
                self._char_battery.set_value(battery_level)
            is_low_battery = 1 if battery_level < self.low_battery_threshold else 0
            if self._char_low_battery.value != is_low_battery:
                self._char_low_battery.set_value(is_low_battery)
                _LOGGER.debug(
                    "%s: Updated battery level to %d", self.entity_id, battery_level
                )

        # Charging state can appear after homekit was started
        if battery_charging is None or not self._char_charging:
            return

        hk_charging = HK_CHARGING if battery_charging else HK_NOT_CHARGING
        if self._char_charging.value != hk_charging:
            self._char_charging.set_value(hk_charging)
            _LOGGER.debug(
                "%s: Updated battery charging to %d", self.entity_id, hk_charging
            )

    @ha_callback
    def async_update_state(self, new_state):
        """Handle state change to update HomeKit value.

        Overridden by accessory types.
        """
        raise NotImplementedError()

    @ha_callback
    def async_call_service(self, domain, service, service_data, value=None):
        """Fire event and call service for changes from HomeKit."""
        event_data = {
            ATTR_ENTITY_ID: self.entity_id,
            ATTR_DISPLAY_NAME: self.display_name,
            ATTR_SERVICE: service,
            ATTR_VALUE: value,
        }
        context = Context()

        self.hass.bus.async_fire(EVENT_HOMEKIT_CHANGED, event_data, context=context)
        self.hass.async_create_task(
            self.hass.services.async_call(
                domain, service, service_data, context=context
            )
        )

    @ha_callback
    def async_reset(self):
        """Reset and recreate an accessory."""
        self.hass.async_create_task(
            self.hass.services.async_call(
                DOMAIN,
                SERVICE_HOMEKIT_RESET_ACCESSORY,
                {ATTR_ENTITY_ID: self.entity_id},
            )
        )

    async def stop(self):
        """Cancel any subscriptions when the bridge is stopped."""
        while self._subscriptions:
            self._subscriptions.pop(0)()


class HomeBridge(Bridge):
    """Adapter class for Bridge."""

    def __init__(self, hass, driver, name):
        """Initialize a Bridge object."""
        super().__init__(driver, name)
        self.set_info_service(
            firmware_revision=__version__,
            manufacturer=MANUFACTURER,
            model=BRIDGE_MODEL,
            serial_number=BRIDGE_SERIAL_NUMBER,
        )
        self.hass = hass

    def setup_message(self):
        """Prevent print of pyhap setup message to terminal."""

    async def async_get_snapshot(self, info):
        """Get snapshot from accessory if supported."""
        if (acc := self.accessories.get(info["aid"])) is None:
            raise ValueError("Requested snapshot for missing accessory")
        if not hasattr(acc, "async_get_snapshot"):
            raise ValueError(
                "Got a request for snapshot, but the Accessory "
                'does not define a "async_get_snapshot" method'
            )
        return await acc.async_get_snapshot(info)


class HomeDriver(AccessoryDriver):
    """Adapter class for AccessoryDriver."""

    def __init__(self, hass, entry_id, bridge_name, entry_title, **kwargs):
        """Initialize a AccessoryDriver object."""
        super().__init__(**kwargs)
        self.hass = hass
        self._entry_id = entry_id
        self._bridge_name = bridge_name
        self._entry_title = entry_title

    @pyhap_callback
    def pair(self, client_uuid, client_public, client_permissions):
        """Override super function to dismiss setup message if paired."""
        success = super().pair(client_uuid, client_public, client_permissions)
        if success:
            async_dismiss_setup_message(self.hass, self._entry_id)
        return success

    @pyhap_callback
    def unpair(self, client_uuid):
        """Override super function to show setup message if unpaired."""
        super().unpair(client_uuid)

        if self.state.paired:
            return

        async_show_setup_message(
            self.hass,
            self._entry_id,
            accessory_friendly_name(self._entry_title, self.accessory),
            self.state.pincode,
            self.accessory.xhm_uri(),
        )
