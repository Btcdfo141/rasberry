"""The myIO integration."""
from datetime import timedelta
import logging

from myio.comms_thread import CommsThread  # pylint: disable=import-error

from homeassistant.const import CONF_NAME
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import slugify

from .const import CONF_REFRESH_TIME, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

COMMS_THREAD = CommsThread()


async def async_setup(hass, config):
    """Set up the myIO-server component."""
    return True


async def async_setup_entry(hass, config_entry):
    """Set up config entry."""
    _LOGGER.debug(DOMAIN)
    _server_name = slugify(config_entry.data[CONF_NAME])
    _server_status = "Offline"
    hass.data[_server_name] = {}
    hass.states.async_set(f"{_server_name}.state", _server_status)
    try:
        _refresh_timer = config_entry.options[CONF_REFRESH_TIME]
    except (ValueError, Exception):  # pylint: disable=broad-except
        _refresh_timer = 4

    def server_status():
        """Return the server status."""
        return hass.states.get(f"{_server_name}.state").state

    def server_data():
        """Return the server data dictionary database."""
        return hass.data[_server_name]

    async def setup_config_entries():
        """Set up myIO platforms with config entry."""

        # Use `hass.async_add_job` to avoid a circular dependency
        # between the platform and the component
        for component in PLATFORMS:
            hass.async_add_job(
                hass.config_entries.async_forward_entry_setup(config_entry, component)
            )

    async def async_update_data():
        """Fetch data from API endpoint."""
        was_offline = False
        _temp_coordinator = hass.data[_server_name]["coordinator"]
        del hass.data[_server_name]["coordinator"]

        if server_status() == "Offline":
            hass.states.async_set(f"{_server_name}.available", False)
            was_offline = True
            for component in PLATFORMS:
                await hass.config_entries.async_forward_entry_unload(
                    config_entry, component
                )

        [hass.data[_server_name], _server_status] = await COMMS_THREAD.send(
            server_data=server_data(),
            server_status=server_status(),
            config_entry=config_entry,
            _post=None,
        )

        hass.states.async_set(f"{_server_name}.state", _server_status)

        if server_status().startswith("Online") and was_offline:
            hass.states.async_set(f"{_server_name}.available", True)
            await setup_config_entries()
            _LOGGER.debug("Online")
        elif not was_offline and server_status() == "Offline":
            _LOGGER.debug("PlatformNotReady")
            hass.data[_server_name]["coordinator"] = _temp_coordinator
            raise PlatformNotReady

        hass.data[_server_name]["coordinator"] = _temp_coordinator

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.pip
        name=f"{_server_name} status",
        update_method=async_update_data,
        # Polling interval.
        update_interval=timedelta(seconds=_refresh_timer),
    )

    hass.data[_server_name]["coordinator"] = coordinator

    await coordinator.async_refresh()

    coordinator.async_add_listener(_server_name)

    return True


async def async_unload_entry(
    hass, config_entry, async_add_devices
):  # async_add_devices because platforms
    """Unload a config entry."""
    for component in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(config_entry, component)
    return True
