"""Support for HomematicIP Cloud devices."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import async_entries_for_config_entry
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .const import (
    CONF_ACCESSPOINT,
    CONF_AUTHTOKEN,
    DOMAIN,
    HMIPC_AUTHTOKEN,
    HMIPC_HAPID,
    HMIPC_NAME,
)
from .generic_entity import HomematicipGenericEntity  # noqa: F401
from .hap import HomematicipAuth, HomematicipHAP  # noqa: F401
from .services import async_setup_services, async_unload_services

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN, default=[]): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Optional(CONF_NAME, default=""): vol.Any(cv.string),
                        vol.Required(CONF_ACCESSPOINT): cv.string,
                        vol.Required(CONF_AUTHTOKEN): cv.string,
                    }
                )
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Set up the HomematicIP Cloud component."""
    hass.data[DOMAIN] = {}

    accesspoints = config.get(DOMAIN, [])

    for conf in accesspoints:
        if conf[CONF_ACCESSPOINT] not in {
            entry.data[HMIPC_HAPID]
            for entry in hass.config_entries.async_entries(DOMAIN)
        }:
            hass.async_add_job(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": config_entries.SOURCE_IMPORT},
                    data={
                        HMIPC_HAPID: conf[CONF_ACCESSPOINT],
                        HMIPC_AUTHTOKEN: conf[CONF_AUTHTOKEN],
                        HMIPC_NAME: conf[CONF_NAME],
                    },
                )
            )

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up an access point from a config entry."""

    # 0.104 introduced config entry unique id, this makes upgrading possible
    if entry.unique_id is None:
        new_data = dict(entry.data)

        hass.config_entries.async_update_entry(
            entry, unique_id=new_data[HMIPC_HAPID], data=new_data
        )

    hap = HomematicipHAP(hass, entry)
    hass.data[DOMAIN][entry.unique_id] = hap

    if not await hap.async_setup():
        return False

    await async_setup_services(hass)
    await async_remove_obsolete_entities(hass, entry)

    # Register on HA stop event to gracefully shutdown HomematicIP Cloud connection
    hap.reset_connection_listener = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP, hap.shutdown
    )

    # Register hap as device in registry.
    device_registry = await dr.async_get_registry(hass)

    home = hap.home
    hapname = home.label if home.label != entry.unique_id else f"Home-{home.label}"

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, home.id)},
        manufacturer="eQ-3",
        # Add the name from config entry.
        name=hapname,
    )
    return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hap = hass.data[DOMAIN].pop(entry.unique_id)
    hap.reset_connection_listener()

    await async_unload_services(hass)

    return await hap.async_reset()


async def async_remove_obsolete_entities(hass: HomeAssistantType, entry: ConfigEntry):
    """Remove obsolete entities from entity registry."""
    entity_registry = await er.async_get_registry(hass)
    er_entries = async_entries_for_config_entry(entity_registry, entry.entry_id)
    for er_entry in er_entries:
        if er_entry.unique_id.startswith("HomematicipAccesspointStatus"):
            entity_registry.async_remove(er_entry.entity_id)
        elif er_entry.unique_id == f"HomematicipBatterySensor_{entry.unique_id}":
            entity_registry.async_remove(er_entry.entity_id)
