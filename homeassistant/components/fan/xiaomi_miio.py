"""
Support for Xiaomi Mi Air Purifier and Xiaomi Mi Air Humidifier.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/fan.xiaomi_miio/
"""
import asyncio
from functools import partial
import logging

import voluptuous as vol

from homeassistant.helpers.entity import ToggleEntity
from homeassistant.components.fan import (FanEntity, PLATFORM_SCHEMA,
                                          SUPPORT_SET_SPEED, DOMAIN, )
from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_TOKEN,
                                 ATTR_ENTITY_ID, )
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Xiaomi Miio Device'
DATA_KEY = 'fan.xiaomi_miio'

CONF_MODEL = 'model'
MODEL_AIRPURIFIER_PRO = 'zhimi.airpurifier.v6'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOKEN): vol.All(cv.string, vol.Length(min=32, max=32)),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MODEL): vol.In(
        ['zhimi.airpurifier.m1',
         'zhimi.airpurifier.m2',
         'zhimi.airpurifier.ma1',
         'zhimi.airpurifier.ma2',
         'zhimi.airpurifier.sa1',
         'zhimi.airpurifier.sa2',
         'zhimi.airpurifier.v1',
         'zhimi.airpurifier.v2',
         'zhimi.airpurifier.v3',
         'zhimi.airpurifier.v5',
         'zhimi.airpurifier.v6',
         'zhimi.humidifier.v1',
         'zhimi.humidifier.ca1']),
})

REQUIREMENTS = ['python-miio==0.3.7']

ATTR_MODEL = 'model'

ATTR_TEMPERATURE = 'temperature'
ATTR_HUMIDITY = 'humidity'
ATTR_AIR_QUALITY_INDEX = 'aqi'
ATTR_MODE = 'mode'
ATTR_FILTER_HOURS_USED = 'filter_hours_used'
ATTR_FILTER_LIFE = 'filter_life_remaining'
ATTR_FAVORITE_LEVEL = 'favorite_level'
ATTR_BUZZER = 'buzzer'
ATTR_CHILD_LOCK = 'child_lock'
ATTR_LED = 'led'
ATTR_LED_BRIGHTNESS = 'led_brightness'
ATTR_MOTOR_SPEED = 'motor_speed'
ATTR_AVERAGE_AIR_QUALITY_INDEX = 'average_aqi'
ATTR_PURIFY_VOLUME = 'purify_volume'
ATTR_BRIGHTNESS = 'brightness'
ATTR_LEVEL = 'level'
ATTR_MOTOR2_SPEED = 'motor2_speed'
ATTR_ILLUMINANCE = 'illuminance'
ATTR_FILTER_RFID_PRODUCT_ID = 'filter_rfid_product_id'
ATTR_FILTER_RFID_TAG = 'filter_rfid_tag'
ATTR_FILTER_TYPE = 'filter_type'
ATTR_LEARN_MODE = 'learn_mode'
ATTR_SLEEP_TIME = 'sleep_time'
ATTR_SLEEP_LEARN_COUNT = 'sleep_mode_learn_count'
ATTR_EXTRA_FEATURES = 'extra_features'
ATTR_TURBO_MODE_SUPPORTED = 'turbo_mode_supported'
ATTR_AUTO_DETECT = 'auto_detect'
ATTR_SLEEP_MODE = 'sleep_mode'

ATTR_TARGET_HUMIDITY = 'target_humidity'
ATTR_TRANS_LEVEL = 'trans_level'
ATTR_FEATURES = 'features'
ATTR_VOLUME = 'volume'

# Map attributes to properties of the state object
AVAILABLE_ATTRIBUTES_AIRPURIFIER_COMMON = {
    ATTR_TEMPERATURE: 'temperature',
    ATTR_HUMIDITY: 'humidity',
    ATTR_AIR_QUALITY_INDEX: 'aqi',
    ATTR_MODE: 'mode',
    ATTR_FILTER_HOURS_USED: 'filter_hours_used',
    ATTR_FILTER_LIFE: 'filter_life_remaining',
    ATTR_FAVORITE_LEVEL: 'favorite_level',
    ATTR_CHILD_LOCK: 'child_lock',
    ATTR_LED: 'led',
    ATTR_MOTOR_SPEED: 'motor_speed',
    ATTR_AVERAGE_AIR_QUALITY_INDEX: 'average_aqi',
    ATTR_PURIFY_VOLUME: 'purify_volume',
    ATTR_LEARN_MODE: 'learn_mode',
    ATTR_SLEEP_TIME: 'sleep_time',
    ATTR_SLEEP_LEARN_COUNT: 'sleep_mode_learn_count',
    ATTR_EXTRA_FEATURES: 'extra_features',
    ATTR_TURBO_MODE_SUPPORTED: 'turbo_mode_supported',
    ATTR_AUTO_DETECT: 'auto_detect',
}

AVAILABLE_ATTRIBUTES_AIRPURIFIER = {
    **AVAILABLE_ATTRIBUTES_AIRPURIFIER_COMMON,
    ATTR_BUZZER: 'buzzer',
    ATTR_LED_BRIGHTNESS: 'led_brightness',
    ATTR_SLEEP_MODE: 'sleep_mode',
}

AVAILABLE_ATTRIBUTES_AIRPURIFIERPRO = {
    **AVAILABLE_ATTRIBUTES_AIRPURIFIER_COMMON,
    ATTR_FILTER_RFID_PRODUCT_ID: 'filter_rfid_product_id',
    ATTR_FILTER_RFID_TAG: 'filter_rfid_tag',
    ATTR_FILTER_TYPE: 'filter_type',
    ATTR_ILLUMINANCE: 'illuminance',
    ATTR_MOTOR2_SPEED: 'motor2_speed',
    ATTR_VOLUME: 'volume',
}

AVAILABLE_ATTRIBUTES_AIRHUMIDIFIER = {
    ATTR_TEMPERATURE: 'temperature',
    ATTR_HUMIDITY: 'humidity',
    ATTR_MODE: 'mode',
    ATTR_BUZZER: 'buzzer',
    ATTR_CHILD_LOCK: 'child_lock',
    ATTR_TRANS_LEVEL: 'trans_level',
    ATTR_TARGET_HUMIDITY: 'target_humidity',
    ATTR_LED_BRIGHTNESS: 'led_brightness',
}

SUCCESS = ['ok']

SUPPORT_SET_BUZZER = 8
SUPPORT_SET_LED = 16
SUPPORT_SET_CHILD_LOCK = 32
SUPPORT_SET_LED_BRIGHTNESS = 64
SUPPORT_SET_FAVORITE_LEVEL = 128
SUPPORT_SET_AUTO_DETECT = 256
SUPPORT_SET_LEARN_MODE = 512
SUPPORT_SET_VOLUME = 1024
SUPPORT_RESET_FILTER = 2048
SUPPORT_SET_EXTRA_FEATURES = 4096
SUPPORT_SET_TARGET_HUMIDITY = 8192

SUPPORT_FLAGS_GENERIC = (SUPPORT_SET_SPEED |
                         SUPPORT_SET_BUZZER |
                         SUPPORT_SET_CHILD_LOCK)

SUPPORT_FLAGS_AIRPURIFIER = (SUPPORT_FLAGS_GENERIC |
                             SUPPORT_SET_LED |
                             SUPPORT_SET_LED_BRIGHTNESS |
                             SUPPORT_SET_FAVORITE_LEVEL |
                             SUPPORT_SET_LEARN_MODE |
                             SUPPORT_RESET_FILTER |
                             SUPPORT_SET_EXTRA_FEATURES)

SUPPORT_FLAGS_AIRPURIFIER_PRO = (SUPPORT_SET_SPEED |
                                 SUPPORT_SET_CHILD_LOCK |
                                 SUPPORT_SET_LED |
                                 SUPPORT_SET_FAVORITE_LEVEL |
                                 SUPPORT_SET_AUTO_DETECT |
                                 SUPPORT_SET_VOLUME)

SUPPORT_FLAGS_AIRHUMIDIFIER = (SUPPORT_FLAGS_GENERIC |
                               SUPPORT_SET_LED_BRIGHTNESS |
                               SUPPORT_SET_TARGET_HUMIDITY)

SERVICE_SET_BUZZER_ON = 'xiaomi_miio_set_buzzer_on'
SERVICE_SET_BUZZER_OFF = 'xiaomi_miio_set_buzzer_off'
SERVICE_SET_LED_ON = 'xiaomi_miio_set_led_on'
SERVICE_SET_LED_OFF = 'xiaomi_miio_set_led_off'
SERVICE_SET_CHILD_LOCK_ON = 'xiaomi_miio_set_child_lock_on'
SERVICE_SET_CHILD_LOCK_OFF = 'xiaomi_miio_set_child_lock_off'
SERVICE_SET_LED_BRIGHTNESS = 'xiaomi_miio_set_led_brightness'
SERVICE_SET_FAVORITE_LEVEL = 'xiaomi_miio_set_favorite_level'
SERVICE_SET_AUTO_DETECT_ON = 'xiaomi_miio_set_auto_detect_on'
SERVICE_SET_AUTO_DETECT_OFF = 'xiaomi_miio_set_auto_detect_off'
SERVICE_SET_LEARN_MODE_ON = 'xiaomi_miio_set_learn_mode_on'
SERVICE_SET_LEARN_MODE_OFF = 'xiaomi_miio_set_learn_mode_off'
SERVICE_SET_VOLUME = 'xiaomi_miio_set_volume'
SERVICE_RESET_FILTER = 'xiaomi_miio_reset_filter'
SERVICE_SET_EXTRA_FEATURES = 'xiaomi_miio_set_extra_features'
SERVICE_SET_TARGET_HUMIDITY = 'xiaomi_miio_set_target_humidity'

AIRPURIFIER_SERVICE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
})

SERVICE_SCHEMA_LED_BRIGHTNESS = AIRPURIFIER_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_BRIGHTNESS):
        vol.All(vol.Coerce(int), vol.Clamp(min=0, max=2))
})

SERVICE_SCHEMA_FAVORITE_LEVEL = AIRPURIFIER_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_LEVEL):
        vol.All(vol.Coerce(int), vol.Clamp(min=0, max=16))
})

SERVICE_SCHEMA_VOLUME = AIRPURIFIER_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_VOLUME):
        vol.All(vol.Coerce(int), vol.Clamp(min=0, max=100))
})

SERVICE_SCHEMA_EXTRA_FEATURES = AIRPURIFIER_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_FEATURES):
        vol.All(vol.Coerce(int), vol.Range(min=0))
})

SERVICE_SCHEMA_TARGET_HUMIDITY = AIRPURIFIER_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_HUMIDITY):
        vol.All(vol.Coerce(int), vol.In([30, 40, 50, 60, 70, 80]))
})

SERVICE_TO_METHOD = {
    SERVICE_SET_BUZZER_ON: {'method': 'async_set_buzzer_on'},
    SERVICE_SET_BUZZER_OFF: {'method': 'async_set_buzzer_off'},
    SERVICE_SET_LED_ON: {'method': 'async_set_led_on'},
    SERVICE_SET_LED_OFF: {'method': 'async_set_led_off'},
    SERVICE_SET_CHILD_LOCK_ON: {'method': 'async_set_child_lock_on'},
    SERVICE_SET_CHILD_LOCK_OFF: {'method': 'async_set_child_lock_off'},
    SERVICE_SET_AUTO_DETECT_ON: {'method': 'async_set_auto_detect_on'},
    SERVICE_SET_AUTO_DETECT_OFF: {'method': 'async_set_auto_detect_off'},
    SERVICE_SET_LEARN_MODE_ON: {'method': 'async_set_learn_mode_on'},
    SERVICE_SET_LEARN_MODE_OFF: {'method': 'async_set_learn_mode_off'},
    SERVICE_RESET_FILTER: {'method': 'async_reset_filter'},
    SERVICE_SET_LED_BRIGHTNESS: {
        'method': 'async_set_led_brightness',
        'schema': SERVICE_SCHEMA_LED_BRIGHTNESS},
    SERVICE_SET_FAVORITE_LEVEL: {
        'method': 'async_set_favorite_level',
        'schema': SERVICE_SCHEMA_FAVORITE_LEVEL},
    SERVICE_SET_VOLUME: {
        'method': 'async_set_volume',
        'schema': SERVICE_SCHEMA_VOLUME},
    SERVICE_SET_EXTRA_FEATURES: {
        'method': 'async_set_extra_features',
        'schema': SERVICE_SCHEMA_EXTRA_FEATURES},
    SERVICE_SET_TARGET_HUMIDITY: {
        'method': 'async_set_target_humidity',
        'schema': SERVICE_SCHEMA_TARGET_HUMIDITY},
}


# pylint: disable=unused-argument
async def async_setup_platform(hass, config, async_add_devices,
                               discovery_info=None):
    """Set up the miio fan device from config."""
    from miio import Device, DeviceException
    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    token = config.get(CONF_TOKEN)
    model = config.get(CONF_MODEL)

    _LOGGER.info("Initializing with host %s (token %s...)", host, token[:5])

    if model is None:
        try:
            miio_device = Device(host, token)
            device_info = miio_device.info()
            model = device_info.model
            _LOGGER.info("%s %s %s detected",
                         model,
                         device_info.firmware_version,
                         device_info.hardware_version)
        except DeviceException:
            raise PlatformNotReady

    if model.startswith('zhimi.airpurifier.'):
        from miio import AirPurifier
        air_purifier = AirPurifier(host, token)
        device = XiaomiAirPurifier(name, air_purifier, model)
    elif model.startswith('zhimi.humidifier.'):
        from miio import AirHumidifier
        air_humidifier = AirHumidifier(host, token)
        device = XiaomiAirHumidifier(name, air_humidifier, model)
    else:
        _LOGGER.error(
            'Unsupported device found! Please create an issue at '
            'https://github.com/syssi/xiaomi_airpurifier/issues '
            'and provide the following data: %s', model)
        return False

    hass.data[DATA_KEY][host] = device
    async_add_devices([device], update_before_add=True)

    async def async_service_handler(service):
        """Map services to methods on XiaomiAirPurifier."""
        method = SERVICE_TO_METHOD.get(service.service)
        params = {key: value for key, value in service.data.items()
                  if key != ATTR_ENTITY_ID}
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        if entity_ids:
            devices = [device for device in hass.data[DATA_KEY].values() if
                       device.entity_id in entity_ids]
        else:
            devices = hass.data[DATA_KEY].values()

        update_tasks = []
        for device in devices:
            await getattr(device, method['method'])(**params)
            update_tasks.append(device.async_update_ha_state(True))

        if update_tasks:
            await asyncio.wait(update_tasks, loop=hass.loop)

    for air_purifier_service in SERVICE_TO_METHOD:
        schema = SERVICE_TO_METHOD[air_purifier_service].get(
            'schema', AIRPURIFIER_SERVICE_SCHEMA)
        hass.services.async_register(
            DOMAIN, air_purifier_service, async_service_handler, schema=schema)


class XiaomiGenericDevice(FanEntity):
    """Representation of a generic Xiaomi device."""

    def __init__(self, name, device, model):
        """Initialize the generic Xiaomi device."""
        self._name = name
        self._device = device
        self._model = model
        self._state = None
        self._state_attrs = {
            ATTR_MODEL: self._model,
        }
        self._supported_features = SUPPORT_FLAGS_GENERIC
        self._skip_update = False

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    @property
    def should_poll(self):
        """Poll the device."""
        return True

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def available(self):
        """Return true when state is known."""
        return self._state is not None

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state_attrs

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @staticmethod
    def _extract_value_from_attribute(state, attribute):
        from enum import Enum

        value = getattr(state, attribute)
        if isinstance(value, Enum):
            return value.value

        return value

    async def _try_command(self, mask_error, func, *args, **kwargs):
        """Call a miio device command handling error messages."""
        from miio import DeviceException
        try:
            result = await self.hass.async_add_job(
                partial(func, *args, **kwargs))

            _LOGGER.debug("Response received from miio device: %s", result)

            return result == SUCCESS
        except DeviceException as exc:
            _LOGGER.error(mask_error, exc)
            return False

    async def async_turn_on(self: ToggleEntity, speed: str = None,
                            **kwargs) -> None:
        """Turn the device on."""
        if speed:
            # If operation mode was set the device must not be turned on.
            result = await self.async_set_speed(speed)
        else:
            result = await self._try_command(
                "Turning the miio device on failed.", self._device.on)

        if result:
            self._state = True
            self._skip_update = True

    async def async_turn_off(self: ToggleEntity, **kwargs) -> None:
        """Turn the device off."""
        result = await self._try_command(
            "Turning the miio device off failed.", self._device.off)

        if result:
            self._state = False
            self._skip_update = True

    async def async_set_buzzer_on(self):
        """Turn the buzzer on."""
        if self.supported_features & SUPPORT_SET_BUZZER == 0:
            return

        await self._try_command(
            "Turning the buzzer of the miio device on failed.",
            self._device.set_buzzer, True)

    async def async_set_buzzer_off(self):
        """Turn the buzzer off."""
        if self.supported_features & SUPPORT_SET_BUZZER == 0:
            return

        await self._try_command(
            "Turning the buzzer of the miio device off failed.",
            self._device.set_buzzer, False)

    async def async_set_child_lock_on(self):
        """Turn the child lock on."""
        if self.supported_features & SUPPORT_SET_CHILD_LOCK == 0:
            return

        await self._try_command(
            "Turning the child lock of the miio device on failed.",
            self._device.set_child_lock, True)

    async def async_set_child_lock_off(self):
        """Turn the child lock off."""
        if self.supported_features & SUPPORT_SET_CHILD_LOCK == 0:
            return

        await self._try_command(
            "Turning the child lock of the miio device off failed.",
            self._device.set_child_lock, False)

    # pylint: disable=no-self-use
    async def async_set_led_on(self):
        """Turn the led on."""
        return

    # pylint: disable=no-self-use
    async def async_set_led_off(self):
        """Turn the led off."""
        return

    # pylint: disable=no-self-use
    async def async_set_favorite_level(self, level: int):
        """Set the favorite level."""
        return

    # pylint: disable=no-self-use
    async def async_set_led_brightness(self, brightness: int):
        """Set the led brightness."""
        return

    # pylint: disable=no-self-use
    async def async_set_target_humidity(self, humidity: int):
        """Set the target humidity."""
        return


class XiaomiAirPurifier(XiaomiGenericDevice, FanEntity):
    """Representation of a Xiaomi Air Purifier."""

    def __init__(self, name, device, model):
        """Initialize the plug switch."""
        XiaomiGenericDevice.__init__(self, name, device, model)

        if self._model == MODEL_AIRPURIFIER_PRO:
            self._supported_features = SUPPORT_FLAGS_AIRPURIFIER_PRO
            self._state_attrs.update({attribute: None for attribute in
                                      AVAILABLE_ATTRIBUTES_AIRPURIFIERPRO})
        else:
            self._supported_features = SUPPORT_FLAGS_AIRPURIFIER
            self._state_attrs.update({attribute: None for attribute in
                                      AVAILABLE_ATTRIBUTES_AIRPURIFIER})

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    async def async_update(self):
        """Fetch state from the device."""
        from miio import DeviceException

        # On state change the device doesn't provide the new state immediately.
        if self._skip_update:
            self._skip_update = False
            return

        try:
            state = await self.hass.async_add_job(
                self._device.status)
            _LOGGER.debug("Got new state: %s", state)

            self._state = state.is_on

            if self._model == MODEL_AIRPURIFIER_PRO:
                self._state_attrs.update(
                    {key: self._extract_value_from_attribute(state, value) for
                     key, value in
                     AVAILABLE_ATTRIBUTES_AIRPURIFIERPRO.items()})
            else:
                self._state_attrs.update(
                    {key: self._extract_value_from_attribute(state, value) for
                     key, value in AVAILABLE_ATTRIBUTES_AIRPURIFIER.items()})

        except DeviceException as ex:
            self._state = None
            _LOGGER.error("Got exception while fetching the state: %s", ex)

    @property
    def speed_list(self: ToggleEntity) -> list:
        """Get the list of available speeds."""
        from miio.airpurifier import OperationMode
        if self._model == MODEL_AIRPURIFIER_PRO:
            return [mode.name for mode in OperationMode if mode.name != 'Idle']

        return [mode.name for mode in OperationMode]

    @property
    def speed(self):
        """Return the current speed."""
        if self._state:
            from miio.airpurifier import OperationMode

            return OperationMode(self._state_attrs[ATTR_MODE]).name

        return None

    async def async_set_speed(self: ToggleEntity, speed: str) -> None:
        """Set the speed of the fan."""
        if self.supported_features & SUPPORT_SET_SPEED == 0:
            return

        from miio.airpurifier import OperationMode

        _LOGGER.debug("Setting the operation mode to: %s", speed)

        await self._try_command(
            "Setting operation mode of the miio device failed.",
            self._device.set_mode, OperationMode[speed.title()])

    async def async_set_led_on(self):
        """Turn the led on."""
        if self.supported_features & SUPPORT_SET_LED == 0:
            return

        await self._try_command(
            "Turning the led of the miio device off failed.",
            self._device.set_led, True)

    async def async_set_led_off(self):
        """Turn the led off."""
        if self.supported_features & SUPPORT_SET_LED == 0:
            return

        await self._try_command(
            "Turning the led of the miio device off failed.",
            self._device.set_led, False)

    async def async_set_led_brightness(self, brightness: int = 2):
        """Set the led brightness."""
        if self.supported_features & SUPPORT_SET_LED_BRIGHTNESS == 0:
            return

        from miio.airpurifier import LedBrightness

        await self._try_command(
            "Setting the led brightness of the miio device failed.",
            self._device.set_led_brightness, LedBrightness(brightness))

    async def async_set_favorite_level(self, level: int = 1):
        """Set the favorite level."""
        if self.supported_features & SUPPORT_SET_FAVORITE_LEVEL == 0:
            return

        await self._try_command(
            "Setting the favorite level of the miio device failed.",
            self._device.set_favorite_level, level)

    async def async_set_auto_detect_on(self):
        """Turn the auto detect on."""
        if self.supported_features & SUPPORT_SET_AUTO_DETECT == 0:
            return

        await self._try_command(
            "Turning the auto detect of the miio device on failed.",
            self._device.set_auto_detect, True)

    async def async_set_auto_detect_off(self):
        """Turn the auto detect off."""
        if self.supported_features & SUPPORT_SET_AUTO_DETECT == 0:
            return

        await self._try_command(
            "Turning the auto detect of the miio device off failed.",
            self._device.set_auto_detect, False)

    async def async_set_learn_mode_on(self):
        """Turn the learn mode on."""
        if self.supported_features & SUPPORT_SET_LEARN_MODE == 0:
            return

        await self._try_command(
            "Turning the learn mode of the miio device on failed.",
            self._device.set_learn_mode, True)

    async def async_set_learn_mode_off(self):
        """Turn the learn mode off."""
        if self.supported_features & SUPPORT_SET_LEARN_MODE == 0:
            return

        await self._try_command(
            "Turning the learn mode of the miio device off failed.",
            self._device.set_learn_mode, False)

    async def async_set_volume(self, volume: int = 50):
        """Set the sound volume."""
        if self.supported_features & SUPPORT_SET_VOLUME == 0:
            return

        await self._try_command(
            "Setting the sound volume of the miio device failed.",
            self._device.set_volume, volume)

    async def async_set_extra_features(self, features: int = 1):
        """Set the extra features."""
        if self.supported_features & SUPPORT_SET_EXTRA_FEATURES == 0:
            return

        await self._try_command(
            "Setting the extra features of the miio device failed.",
            self._device.set_extra_features, features)

    async def async_reset_filter(self):
        """Reset the filter lifetime and usage."""
        if self.supported_features & SUPPORT_RESET_FILTER == 0:
            return

        await self._try_command(
            "Resetting the filter lifetime of the miio device failed.",
            self._device.reset_filter)


class XiaomiAirHumidifier(XiaomiGenericDevice, FanEntity):
    """Representation of a Xiaomi Air Humidifier."""

    def __init__(self, name, device, model):
        """Initialize the plug switch."""
        XiaomiGenericDevice.__init__(self, name, device, model)

        self._supported_features = SUPPORT_FLAGS_AIRHUMIDIFIER
        self._state_attrs.update({attribute: None for attribute in
                                  AVAILABLE_ATTRIBUTES_AIRHUMIDIFIER})

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    async def async_update(self):
        """Fetch state from the device."""
        from miio import DeviceException

        # On state change the device doesn't provide the new state immediately.
        if self._skip_update:
            self._skip_update = False
            return

        try:
            state = await self.hass.async_add_job(
                self._device.status)
            _LOGGER.debug("Got new state: %s", state)

            self._state = state.is_on

            self._state_attrs.update(
                {key: self._extract_value_from_attribute(state, value) for
                 key, value in AVAILABLE_ATTRIBUTES_AIRHUMIDIFIER.items()})

        except DeviceException as ex:
            self._state = None
            _LOGGER.error("Got exception while fetching the state: %s", ex)

    @property
    def speed_list(self: ToggleEntity) -> list:
        """Get the list of available speeds."""
        from miio.airhumidifier import OperationMode
        return [mode.name for mode in OperationMode]

    @property
    def speed(self):
        """Return the current speed."""
        if self._state:
            from miio.airhumidifier import OperationMode

            return OperationMode(self._state_attrs[ATTR_MODE]).name

        return None

    async def async_set_speed(self: ToggleEntity, speed: str) -> None:
        """Set the speed of the fan."""
        if self.supported_features & SUPPORT_SET_SPEED == 0:
            return

        from miio.airhumidifier import OperationMode

        _LOGGER.debug("Setting the operation mode to: %s", speed)

        await self._try_command(
            "Setting operation mode of the miio device failed.",
            self._device.set_mode, OperationMode[speed.title()])

    async def async_set_led_brightness(self, brightness: int = 2):
        """Set the led brightness."""
        if self.supported_features & SUPPORT_SET_LED_BRIGHTNESS == 0:
            return

        from miio.airhumidifier import LedBrightness

        await self._try_command(
            "Setting the led brightness of the miio device failed.",
            self._device.set_led_brightness, LedBrightness(brightness))

    async def async_set_target_humidity(self, humidity: int = 40):
        """Set the target humidity."""
        if self.supported_features & SUPPORT_SET_TARGET_HUMIDITY == 0:
            return

        await self._try_command(
            "Setting the target humidity of the miio device failed.",
            self._device.set_target_humidity, humidity)
