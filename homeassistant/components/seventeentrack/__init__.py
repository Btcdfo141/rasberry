"""The seventeentrack component."""
from datetime import timedelta
import logging

from py17track.client import Client
from py17track.errors import SeventeenTrackError
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_FRIENDLY_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .config_flow import get_client
from .const import (
    CONF_ACCOUNT,
    CONF_SHOW_ARCHIVED,
    CONF_TRACKING_NUMBER,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SHOW_ARCHIVED,
    DOMAIN,
    SERVICE_ADD_PACKAGE,
)
from .errors import AuthenticationError, UnknownError

_LOGGER = logging.getLogger(__name__)


SERVICE_ADD_PACKAGE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCOUNT): cv.string,
        vol.Required(CONF_TRACKING_NUMBER): cv.string,
        vol.Optional(CONF_FRIENDLY_NAME): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the SeventeenTrack component."""
    coordinator = SeventeenTrackDataCoordinator(hass, config_entry)

    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload SeventeenTrack Entry from config_entry."""

    await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    hass.data[DOMAIN].pop(config_entry.entry_id)

    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_ADD_PACKAGE)
        del hass.data[DOMAIN]

    return True


class SeventeenTrackDataCoordinator(DataUpdateCoordinator):
    """Get the latest data from SeventeenTrack."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the data object."""
        self.hass = hass
        self.config_entry = config_entry
        self.client: Client = None
        super().__init__(
            self.hass,
            _LOGGER,
            name=DOMAIN,
            update_method=self.async_update,
            update_interval=timedelta(
                minutes=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
            ),
        )

    @property
    def show_archived(self) -> bool:
        """Include archived packages when fetching data."""
        return self.config_entry.options.get(CONF_SHOW_ARCHIVED, DEFAULT_SHOW_ARCHIVED)

    async def async_update(self) -> dict:
        """Update SeventeenTrack data."""
        try:
            packages = await self.client.profile.packages(
                show_archived=False, tz=str(self.hass.config.time_zone)
            )
            summary = await self.client.profile.summary(show_archived=False)

            if self.show_archived:
                archived_packages = await self.client.profile.packages(
                    show_archived=True, tz=str(self.hass.config.time_zone)
                )
                packages += archived_packages

                archived_summary = await self.client.profile.summary(show_archived=True)
                for status, qty in archived_summary.items():
                    summary[status] += qty

        except SeventeenTrackError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        _LOGGER.debug("New package data received: %s", packages)
        _LOGGER.debug("New summary data received: %s", summary)

        return {"packages": packages, "summary": summary}

    async def async_setup(self) -> bool:
        """Set up SeventeenTrack."""
        try:
            self.client = await get_client(self.hass, self.config_entry.data)

        except AuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except UnknownError as err:
            _LOGGER.error("There was an error while logging in: %s", err)
            raise ConfigEntryNotReady from err

        async def async_add_package(service: ServiceCall):
            """Add new package."""
            device_registry = self.hass.helpers.device_registry.async_get(self.hass)
            device = device_registry.async_get(service.data[CONF_ACCOUNT])
            for config_entry_id in device.config_entries:
                client = self.hass.data[DOMAIN][config_entry_id].client
                break
            await client.profile.add_package(
                service.data[CONF_TRACKING_NUMBER], service.data[CONF_FRIENDLY_NAME]
            )
            await self.async_request_refresh()

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_ADD_PACKAGE,
            async_add_package,
            schema=SERVICE_ADD_PACKAGE_SCHEMA,
        )
        self.config_entry.add_update_listener(self.async_options_updated)

        return True

    @staticmethod
    async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry):
        """Triggered by config entry options updates."""
        hass.data[DOMAIN][entry.entry_id].update_interval = timedelta(
            minutes=entry.options[CONF_SCAN_INTERVAL]
        )
        await hass.data[DOMAIN][entry.entry_id].async_request_refresh()
