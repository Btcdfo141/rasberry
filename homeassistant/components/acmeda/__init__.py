"""The Rollease Acmeda Automate integration."""
import asyncio
import ipaddress

import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.const import CONF_HOST
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .hub import PulseHub

CONF_HUBS = "hubs"

HUB_CONFIG_SCHEMA = vol.Schema(
    {
        # Validate as IP address and then convert back to a string.
        vol.Required(CONF_HOST): vol.All(ipaddress.ip_address, cv.string),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_HUBS): vol.All(
                    cv.ensure_list, [vol.All(HUB_CONFIG_SCHEMA)],
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["cover", "sensor"]


async def async_setup(hass: core.HomeAssistant, config: dict):
    """Set up the Rollease Acmeda Automate component."""
    conf = config.get(DOMAIN)
    if conf is None:
        conf = {}

    hass.data[DOMAIN] = {}

    # User has configured hubs
    if CONF_HUBS not in conf:
        return True

    hubs = conf[CONF_HUBS]

    configured_hubs = {
        entry.data["host"] for entry in hass.config_entries.async_entries(DOMAIN)
    }

    for hub_conf in hubs:
        host = hub_conf[CONF_HOST]

        if host in configured_hubs:
            continue

        # No existing config entry found, trigger link config flow. Because we're
        # inside the setup of this component we'll have to use hass.async_add_job
        # to avoid a deadlock: creating a config entry will set up the component
        # but the setup would block till the entry is created!
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data={"host": hub_conf[CONF_HOST]},
            )
        )

    return True


async def async_setup_entry(
    hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Set up Rollease Acmeda Automate hub from a config entry."""
    hub = PulseHub(hass, config_entry)

    if not await hub.async_setup():
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = hub

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    return True


async def async_unload_entry(
    hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Unload a config entry."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if not await hub.async_reset():
        return False

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok
