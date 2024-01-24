"""Support for Lupusec Home Security system."""
import logging

import lupupy
from lupupy.exceptions import LupusecException
import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "lupusec"

NOTIFICATION_ID = "lupusec_notification"
NOTIFICATION_TITLE = "Lupusec Security Setup"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_IP_ADDRESS): cv.string,
                vol.Optional(CONF_NAME): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

LUPUSEC_PLATFORMS = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the lupusec integration."""

    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    username = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)
    host = conf.get(CONF_IP_ADDRESS)
    name = conf.get(CONF_NAME)

    # Explicitly added in the config file, create a config entry.
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
                CONF_HOST: host,
                CONF_NAME: name,
            },
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""

    hass.data.setdefault(DOMAIN, {})

    host = entry.data.get(CONF_HOST)
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    name = entry.data.get(CONF_NAME)

    try:
        lupusec_system = await hass.async_add_executor_job(
            LupusecSystem, username, password, host, name
        )
        hass.data[DOMAIN] = lupusec_system
    except LupusecException as ex:
        _LOGGER.error(ex)

        persistent_notification.create(
            hass,
            f"Error: {ex}<br />You will need to restart hass after fixing.",
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID,
        )
        return False

    for platform in LUPUSEC_PLATFORMS:
        hass.async_add_job(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


class LupusecSystem:
    """Lupusec System class."""

    def __init__(self, username, password, ip_address, name) -> None:
        """Initialize the system."""
        self.lupusec = lupupy.Lupusec(username, password, ip_address)
        self.name = name


class LupusecDevice(Entity):
    """Representation of a Lupusec device."""

    _attr_has_entity_name = True

    def __init__(self, data, device, config_entry=None) -> None:
        """Initialize a sensor for Lupusec device."""
        self._data = data
        self._device = device
        self._entry_id = ""

        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id if config_entry else "_none"

    def update(self):
        """Update automation state."""
        self._device.refresh()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._device.name

    @property
    def device_info(self):
        """Return device information about the sensor."""
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"Lupusec-XT{self._data.lupusec.model}",
            "manufacturer": "Lupus Electronics",
            "model": f"Lupusec-XT{self._data.lupusec.model}",
            "via_device": (DOMAIN, "lupusec_state"),
        }
