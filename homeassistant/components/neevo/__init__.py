"""The Nee-Vo Tank Monitoring integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from aiohttp.client_exceptions import ClientError
from pyneevo import NeeVoApiInterface
from pyneevo.errors import (
    GenericHTTPError,
    InvalidCredentialsError,
    InvalidResponseFormat,
    PyNeeVoError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, TANKS

_LOGGER = logging.getLogger(__name__)

PUSH_UPDATE = "neevo.push_update"
INTERVAL = 60

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Nee-Vo Tank Monitoring from a config entry."""

    email = config_entry.data[CONF_EMAIL]
    password = config_entry.data[CONF_PASSWORD]

    try:
        api = await NeeVoApiInterface.login(email, password=password)
    except InvalidCredentialsError:
        _LOGGER.error("Invalid credentials provided")
        return False
    except PyNeeVoError as err:
        _LOGGER.error("Config entry failed: %s", err)
        raise ConfigEntryNotReady from err

    try:
        tanks = await api.get_tanks_info()
    except (ClientError, GenericHTTPError, InvalidResponseFormat) as err:
        raise ConfigEntryNotReady from err

    async def fetch_update():
        """Fetch the latest changes from the API."""
        try:
            return await api.get_tanks_info()
        except PyNeeVoError as err:
            raise UpdateFailed(err) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Neevo",
        update_method=fetch_update,
        update_interval=timedelta(minutes=INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        "coordinator": coordinator,
        TANKS: tanks,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


class NeeVoEntity(CoordinatorEntity):
    """Define a base Nee-Vo entity."""

    _attr_should_poll = False

    def __init__(self, instance: dict[str, Any], tank_id: str) -> None:
        """Initialize."""
        super().__init__(instance["coordinator"])
        self._neevo = self.coordinator.data[tank_id]
        self._attr_name = self._neevo.name
        self._attr_unique_id = f"{self._neevo.id}_{self._neevo.name}"

    async def async_added_to_hass(self):
        """Subscribe to device events."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, PUSH_UPDATE, self.on_update_received)
        )

    @callback
    def on_update_received(self):
        """Update was pushed from the Nee-Vo API."""
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._neevo.id)},
            manufacturer="OTODATA",
            name=self._neevo.name,
        )
