"""
Support for KNX/IP binary sensors via XKNX.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.xknx/
"""
import asyncio
import xknx
import voluptuous as vol

from homeassistant.components.xknx import DATA_XKNX
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, \
    BinarySensorDevice
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.script import Script

CONF_ADDRESS = 'address'
CONF_DEVICE_CLASS = 'device_class'
CONF_SIGNIFICANT_BIT = 'significant_bit'
CONF_DEFAULT_SIGNIFICANT_BIT = 1
CONF_AUTOMATION = 'automation'
CONF_HOOK = 'hook'
CONF_DEFAULT_HOOK = 'on'
CONF_COUNTER = 'counter'
CONF_DEFAULT_COUNTER = 1
CONF_ACTION = 'action'

CONF__ACTION = 'turn_off_action'

DEFAULT_NAME = 'XKNX Binary Sensor'
DEPENDENCIES = ['xknx']

AUTOMATION_SCHEMA = vol.Schema({
    vol.Optional(CONF_HOOK, default=CONF_DEFAULT_HOOK): cv.string,
    vol.Optional(CONF_COUNTER, default=CONF_DEFAULT_COUNTER): cv.port,
    vol.Required(CONF_ACTION, default=None): cv.SCRIPT_SCHEMA
})

AUTOMATIONS_SCHEMA = vol.All(
    cv.ensure_list,
    [AUTOMATION_SCHEMA]
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ADDRESS): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_DEVICE_CLASS): cv.string,
    vol.Optional(CONF_SIGNIFICANT_BIT, default=CONF_DEFAULT_SIGNIFICANT_BIT):
        cv.positive_int,
    vol.Optional(CONF_AUTOMATION, default=None): AUTOMATIONS_SCHEMA,
})


@asyncio.coroutine
def async_setup_platform(hass, config, add_devices,
                         discovery_info=None):
    """Set up binary sensor(s) for XKNX platform."""
    if DATA_XKNX not in hass.data \
            or not hass.data[DATA_XKNX].initialized:
        return False

    if discovery_info is not None:
        yield from add_devices_from_component(hass, add_devices)
    else:
        yield from add_devices_from_platform(hass, config, add_devices)

    return True


@asyncio.coroutine
def add_devices_from_component(hass, add_devices):
    """Set up binary sensors for XKNX platform configured via xknx.yaml."""
    entities = []
    for device in hass.data[DATA_XKNX].xknx.devices:
        if isinstance(device, xknx.devices.BinarySensor) and \
                not hasattr(device, "already_added_to_hass"):
            entities.append(XKNXBinarySensor(hass, device))
    add_devices(entities)


@asyncio.coroutine
def add_devices_from_platform(hass, config, add_devices):
    """Set up binary senor for XKNX platform configured within plattform."""
    name = config.get(CONF_NAME)
    binary_sensor = xknx.devices.BinarySensor(
        hass.data[DATA_XKNX].xknx,
        name=name,
        group_address=config.get(CONF_ADDRESS),
        device_class=config.get(CONF_DEVICE_CLASS),
        significant_bit=config.get(CONF_SIGNIFICANT_BIT))

    automations = config.get(CONF_AUTOMATION)
    if automations is not None:
        for automation in automations:
            counter = automation.get(CONF_COUNTER)
            hook = automation.get(CONF_HOOK)
            action = automation.get(CONF_ACTION)
            automation = XKNXAutomation(
                hass=hass,
                hook=hook,
                counter=counter,
                action=action,
                name="{} turn ON script".format(name))
            binary_sensor.actions.append(automation)

    binary_sensor.already_added_to_hass = True
    hass.data[DATA_XKNX].xknx.devices.add(binary_sensor)
    add_devices([XKNXBinarySensor(hass, binary_sensor)])


class XKNXAutomation(xknx.devices.ActionBase):
    """Base Class for handling commands triggered by KNX bus."""

    def __init__(self, hass, hook, action, name, counter=1):
        """Initialize XKNXAutomation class."""
        super(XKNXAutomation, self).__init__(
            hass.data[DATA_XKNX].xknx, hook, counter)
        self.hass = hass
        self.script = Script(hass, action, name)

    @asyncio.coroutine
    def execute(self):
        """Execute action."""
        yield from self.script.async_run()


class XKNXBinarySensor(BinarySensorDevice):
    """Representation of a XKNX binary sensor."""

    def __init__(self, hass, device):
        """Initialization of XKNXBinarySensor."""
        self.device = device
        self.hass = hass
        self.register_callbacks()

    def register_callbacks(self):
        """Register callbacks to update hass after device was changed."""
        @asyncio.coroutine
        def after_update_callback(device):
            """Callback after device was updated."""
            # pylint: disable=unused-argument
            yield from self.async_update_ha_state()
        self.device.register_device_updated_cb(after_update_callback)

    @property
    def name(self):
        """Return the name of the XKNX device."""
        return self.device.name

    @property
    def should_poll(self):
        """No polling needed within XKNX."""
        return False

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self.device.device_class

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self.device.is_on()
