"""Support for Etekcity VeSync switches."""
import logging
from homeassistant.components.switch import (SwitchDevice)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .common import CONF_SWITCHES, async_add_entities_retry
from .const import VS_DISCOVERY, VS_DISPATCHERS

_LOGGER = logging.getLogger(__name__)

ENERGY_UPDATE_INT = 21600

DOMAIN = 'vesync'


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up switches."""
    async def async_discover(dev_len):
        if dev_len > 0:
            dev_slice = hass.data[DOMAIN][CONF_SWITCHES][-dev_len:]
            for dev in dev_slice:
                await _async_setup_entity(dev, async_add_entities)

    disp = async_dispatcher_connect(
        hass, VS_DISCOVERY.format(CONF_SWITCHES), async_discover)

    hass.data[DOMAIN][VS_DISPATCHERS].append(disp)
    _LOGGER.debug('SWITCH ENTITY RETRY CALLED')
    await async_add_entities_retry(
        hass,
        async_add_entities,
        hass.data[DOMAIN][CONF_SWITCHES],
        _async_setup_entity
    )
    return True


async def _async_setup_entity(device, async_add_entities):
    """Check if device is online and add entity."""
    async_add_entities(
        [VeSyncSwitchHA(device)],
        update_before_add=True
    )


class VeSyncSwitchHA(SwitchDevice):
    """Representation of a VeSync switch."""

    def __init__(self, plug):
        """Initialize the VeSync switch device."""
        self.smartplug = plug

    @property
    def unique_id(self):
        """Return the ID of this switch."""
        if isinstance(self.smartplug.sub_device_no, int):
            return (self.smartplug.cid + str(self.smartplug.sub_device_no))
        else:
            return self.smartplug.cid

    @property
    def name(self):
        """Return the name of the switch."""
        return self.smartplug.device_name

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attr = {}
        attr['active_time'] = self.smartplug.active_time
        if hasattr(self.smartplug, 'weekly_energy_total'):
            attr['voltage'] = self.smartplug.voltage
            attr['weekly_energy_total'] = self.smartplug.weekly_energy_total
            attr['monthly_energy_total'] = self.smartplug.monthly_energy_total
            attr['yearly_energy_total'] = self.smartplug.yearly_energy_total
        return attr

    @property
    def current_power_w(self):
        """Return the current power usage in W."""
        if hasattr(self.smartplug, 'power'):
            return self.smartplug.power

    @property
    def today_energy_kwh(self):
        """Return the today total energy usage in kWh."""
        if hasattr(self.smartplug, 'energy_today'):
            return self.smartplug.energy_today

    @property
    def available(self) -> bool:
        """Return True if switch is available."""
        return self.smartplug.connection_status == "online"

    @property
    def is_on(self):
        """Return True if switch is on."""
        return self.smartplug.device_status == "on"

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self.smartplug.turn_on()

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self.smartplug.turn_off()

    def update(self):
        """Handle data changes for node values."""
        self.smartplug.update()
        try:
            self.smartplug.update_energy()
        except AttributeError:
            pass
