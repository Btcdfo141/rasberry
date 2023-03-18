"""The foscam component."""

from datetime import timedelta

import async_timeout
from libpyfoscam import FoscamCamera

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_registry import async_migrate_entries
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .config_flow import DEFAULT_RTSP_PORT
from .const import CONF_RTSP_PORT, DOMAIN, LOGGER, SERVICE_PTZ, SERVICE_PTZ_PRESET

PLATFORMS = [Platform.CAMERA, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up foscam from a config entry."""

    session = FoscamCamera(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        verbose=False,
    )
    coordinator = FoscamCoordinator(hass, session)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "session": session,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        if not hass.data[DOMAIN]:
            hass.services.async_remove(domain=DOMAIN, service=SERVICE_PTZ)
            hass.services.async_remove(domain=DOMAIN, service=SERVICE_PTZ_PRESET)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    LOGGER.debug("Migrating from version %s", entry.version)

    if entry.version == 1:
        # Change unique id
        @callback
        def update_unique_id(entry):
            return {"new_unique_id": entry.entry_id}

        await async_migrate_entries(hass, entry.entry_id, update_unique_id)

        entry.unique_id = None

        # Get RTSP port from the camera or use the fallback one and store it in data
        camera = FoscamCamera(
            entry.data[CONF_HOST],
            entry.data[CONF_PORT],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            verbose=False,
        )

        ret, response = await hass.async_add_executor_job(camera.get_port_info)

        rtsp_port = DEFAULT_RTSP_PORT

        if ret != 0:
            rtsp_port = response.get("rtspPort") or response.get("mediaPort")

        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_RTSP_PORT: rtsp_port}
        )

        # Change entry version
        entry.version = 2

    LOGGER.info("Migration to version %s successful", entry.version)

    return True


class FoscamCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, session, update_interval=timedelta(seconds=30)):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            LOGGER,
            # Name of the data. For logging purposes.
            name=DOMAIN,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=update_interval,
        )
        self._session = session

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            async with async_timeout.timeout(30):
                data = {}
                ret, dev_info = await self.hass.async_add_executor_job(
                    self._session.get_dev_info
                )
                if ret == 0:
                    data["dev_info"] = dev_info
                data["product_info"] = (
                    await self.hass.async_add_executor_job(
                        self._session.get_product_all_info
                    )
                )[1]
                ret, is_asleep = await self.hass.async_add_executor_job(
                    self._session.is_asleep
                )
                data["is_asleep"] = {"supported": ret == 0, "status": is_asleep}
                return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
