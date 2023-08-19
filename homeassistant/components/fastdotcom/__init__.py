"""Support for testing internet speed via Fast.com."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from fastdotcom import fast_com
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .const import CONF_MANUAL, DATA_UPDATED, DEFAULT_INTERVAL, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_INTERVAL): vol.All(
                    cv.time_period, cv.positive_timedelta
                ),
                vol.Optional(CONF_MANUAL, default=False): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_platform(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Fast.com component."""
    conf = config[DOMAIN]
    data = hass.data[DOMAIN] = SpeedtestData(hass)

    if not conf[CONF_MANUAL]:
        async_track_time_interval(hass, data.update, conf[CONF_SCAN_INTERVAL])

    async def update(service_call: ServiceCall | None = None) -> None:
        """Service call to manually update the data."""
        await data.update()

    hass.services.async_register(DOMAIN, "speedtest", update)

    hass.async_create_task(
        async_load_platform(hass, Platform.SENSOR, DOMAIN, {}, config)
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Fast.com component."""
    # conf = entry.data[DOMAIN]
    data = hass.data[DOMAIN] = SpeedtestData(hass)
    await data.update()

    async_track_time_interval(hass, data.update, timedelta(hours=DEFAULT_INTERVAL))

    async def update(service_call: ServiceCall | None = None) -> None:
        """Service call to manually update the data."""
        await data.update()

    hass.services.async_register(DOMAIN, "speedtest", update)

    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Fast.com config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


# Legacy support for the Platform. Not sure at the moment if this is needed.
class SpeedtestData:
    """Get the latest data from Fast.com."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the data object."""
        self.data: dict[str, Any] | None = None
        self._hass = hass

    async def update(self, now: datetime | None = None) -> None:
        """Get the latest data from fast.com."""
        _LOGGER.debug("Executing Fast.com speedtest")
        fast_com_data = await self._hass.async_add_executor_job(fast_com)
        self.data = {"download": fast_com_data}
        _LOGGER.debug("Fast.com speedtest finished, with mbit/s: %s", fast_com_data)
        dispatcher_send(self._hass, DATA_UPDATED)
