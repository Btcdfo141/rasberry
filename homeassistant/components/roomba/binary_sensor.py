"""Roomba binary sensor entities."""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity

from . import roomba_reported_state
<<<<<<< HEAD
from .const import BLID, DOMAIN, ROOMBA_SESSION
from .irobot_base import IRobotEntity
=======
from .const import BLID, DOMAIN, ICON_BIN, ROOMBA_SESSION
>>>>>>> Fix icon

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the iRobot Roomba vacuum cleaner."""
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    roomba = domain_data[ROOMBA_SESSION]
    blid = domain_data[BLID]
    status = roomba_reported_state(roomba).get("bin", {})
    if "full" in status:
        roomba_vac = RoombaBinStatus(roomba, blid)
        async_add_entities([roomba_vac], True)


class RoombaBinStatus(IRobotEntity, BinarySensorEntity):
    """Class to hold Roomba Sensor basic info."""

<<<<<<< HEAD
    ICON = "mdi:delete-variant"
=======
    def __init__(self, roomba, blid):
        """Initialize the sensor object."""
        self.vacuum = roomba
        self.vacuum_state = roomba_reported_state(roomba)
        self._blid = blid
        self._name = self.vacuum_state.get("name")
        self._identifier = f"roomba_{self._blid}"
        self._bin_status = None
>>>>>>> Fix icon

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} Bin Full"

    @property
    def unique_id(self):
        """Return the ID of this sensor."""
        return f"bin_{self._blid}"

    @property
    def icon(self):
        """Return the icon of this sensor."""
        return ICON_BIN

    @property
    def state(self):
        """Return the state of the sensor."""
        return roomba_reported_state(self.vacuum).get("bin", {}).get("full", False)
