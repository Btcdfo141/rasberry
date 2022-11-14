"""The elmax-cloud integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from elmax_api.http import Elmax, ElmaxLocal, GenericElmax
from elmax_api.model.panel import PanelEntry

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .common import ElmaxCoordinator, DummyPanel, get_direct_api_url
from .const import (
    CONF_ELMAX_MODE,
    CONF_ELMAX_MODE_CLOUD,
    CONF_ELMAX_MODE_DIRECT,
    CONF_ELMAX_MODE_DIRECT_HOST,
    CONF_ELMAX_MODE_DIRECT_PORT,
    CONF_ELMAX_MODE_DIRECT_SSL,
    CONF_ELMAX_PANEL_ID,
    CONF_ELMAX_PANEL_PIN,
    CONF_ELMAX_PASSWORD,
    CONF_ELMAX_USERNAME,
    DOMAIN,
    ELMAX_PLATFORMS,
    POLLING_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


async def _load_elmax_panel_client(entry: ConfigEntry) -> (GenericElmax, PanelEntry):
    # Use a null-safe getter for the mode, as this attribute has been
    # added later than first revisions. When null, assume cloud.
    client = None
    mode = entry.data.get(CONF_ELMAX_MODE, CONF_ELMAX_MODE_CLOUD)
    panel = None
    if mode == CONF_ELMAX_MODE_CLOUD:
        client = Elmax(
            username=entry.data[CONF_ELMAX_USERNAME],
            password=entry.data[CONF_ELMAX_PASSWORD],
        )
        client.set_current_panel(
            entry.data[CONF_ELMAX_PANEL_ID], entry.data[CONF_ELMAX_PANEL_PIN]
        )
        # Make sure the panel is online and assigned to the current user
        panel = await _check_cloud_panel_status(client, entry.data[CONF_ELMAX_PANEL_ID])
    elif mode == CONF_ELMAX_MODE_DIRECT:
        client_api_url = get_direct_api_url(host=entry.data[CONF_ELMAX_MODE_DIRECT_HOST],
                                            port=entry.data[CONF_ELMAX_MODE_DIRECT_PORT],
                                            ssl=entry.data[CONF_ELMAX_MODE_DIRECT_SSL])
        client = ElmaxLocal(
            panel_api_url=client_api_url,
            panel_code=entry.data[CONF_ELMAX_PANEL_PIN],
        )
        panel = DummyPanel(panel_uri=client_api_url)
    return client, panel


async def _check_cloud_panel_status(client: Elmax, panel_id: str) -> PanelEntry:
    """Perform integrity checks against the cloud for panel-user association."""
    # Retrieve the panel online status first
    panels = await client.list_control_panels()
    panel = next((panel for panel in panels if panel.hash == panel_id), None)

    # If the panel is no more available within the ones associated to that client, raise
    # a config error as the user must reconfigure it in order to  make it work again
    if not panel:
        raise ConfigEntryAuthFailed(
            f"Panel ID {panel_id} is no more linked to this user account"
        )
    return panel


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up elmax-cloud from a config entry."""
    client, panel = await _load_elmax_panel_client(entry)

    # Create the API client object and attempt a login, so that we immediately know
    # if there is something wrong with user credentials
    coordinator = ElmaxCoordinator(
        hass=hass,
        logger=_LOGGER,
        elmax_api_client=client,
        panel=panel,
        name=f"Elmax Cloud {entry.entry_id}",
        update_interval=timedelta(seconds=POLLING_SECONDS),
    )

    # Issue a first refresh, so that we trigger a re-auth flow if necessary
    await coordinator.async_config_entry_first_refresh()

    # Store a global reference to the coordinator for later use
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Perform platform initialization.
    await hass.config_entries.async_forward_entry_setups(entry, ELMAX_PLATFORMS)
    return True


async def update_listener(hass, entry):
    """Handle options and config-entry update."""
    coordinator: ElmaxCoordinator = hass.data[DOMAIN][entry.entry_id]
    # Get a fresh/updated HTTP Client to be used with the coordinator.
    client, panel = await _load_elmax_panel_client(entry)
    coordinator.http_client = client


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ELMAX_PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
