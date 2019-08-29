"""Support for Tuya switches."""
from homeassistant.components.switch import ENTITY_ID_FORMAT, SwitchDevice

from . import DATA_TUYA, TuyaDevice


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up Tuya Switch device."""
    if discovery_info is None:
        return
    tuya = hass.data[DATA_TUYA]
    dev_ids = discovery_info.get("dev_ids")
    devices = []
    for dev_id in dev_ids:
        device = tuya.get_device_by_id(dev_id)
        if device is None:
            continue
        devices.append(TuyaSwitch(device))
    add_entities(devices)


class TuyaSwitch(TuyaDevice, SwitchDevice):
    """Tuya Switch Device."""

    def __init__(self, tuya):
        """Init Tuya switch device."""
        super().__init__(tuya)
        self.entity_id = ENTITY_ID_FORMAT.format(tuya.object_id())
        self._is_on = False

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._is_on

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self.tuya.turn_on()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self.tuya.turn_off()

    def update(self):
        """Update switch device."""
        self._is_on = self.tuya.state()
