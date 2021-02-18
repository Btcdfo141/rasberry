"""Integration providing core pieces of infrastructure."""
import asyncio
import itertools as it
import logging

import voluptuous as vol

from homeassistant.auth.permissions.const import CAT_ENTITIES, POLICY_CONTROL
import homeassistant.config as conf_util
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    RESTART_EXIT_CODE,
    SERVICE_HOMEASSISTANT_RESTART,
    SERVICE_HOMEASSISTANT_STOP,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
import homeassistant.core as ha
from homeassistant.exceptions import HomeAssistantError, Unauthorized, UnknownUser
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_referenced_entity_ids

ATTR_CONFIG_ENTRY_ID = "config_entry_id"

_LOGGER = logging.getLogger(__name__)
DOMAIN = ha.DOMAIN
SERVICE_RELOAD_CORE_CONFIG = "reload_core_config"
SERVICE_RELOAD_CONFIG_ENTRY = "reload_config_entry"
SERVICE_CHECK_CONFIG = "check_config"
SERVICE_UPDATE_ENTITY = "update_entity"
SERVICE_SET_LOCATION = "set_location"
SCHEMA_UPDATE_ENTITY = vol.Schema({ATTR_ENTITY_ID: cv.entity_ids})
SCHEMA_RELOAD_CONFIG_ENTRY = vol.Schema({vol.Required(ATTR_CONFIG_ENTRY_ID): str})


async def async_setup(hass: ha.HomeAssistant, config: dict) -> bool:
    """Set up general services related to Home Assistant."""

    async def async_handle_turn_service(service):
        """Handle calls to homeassistant.turn_on/off."""
        referenced = await async_extract_referenced_entity_ids(hass, service)
        all_referenced = referenced.referenced | referenced.indirectly_referenced

        # Generic turn on/off method requires entity id
        if not all_referenced:
            _LOGGER.error(
                "homeassistant.%s cannot be called without a target", service.service
            )
            return

        # Group entity_ids by domain. groupby requires sorted data.
        by_domain = it.groupby(
            sorted(all_referenced), lambda item: ha.split_entity_id(item)[0]
        )

        tasks = []
        unsupported_entities = set()

        for domain, ent_ids in by_domain:
            # This leads to endless loop.
            if domain == DOMAIN:
                _LOGGER.warning(
                    "Called service homeassistant.%s with invalid entities %s",
                    service.service,
                    ", ".join(ent_ids),
                )
                continue

            if not hass.services.has_service(domain, service.service):
                unsupported_entities.update(set(ent_ids) & referenced.referenced)
                continue

            # Create a new dict for this call
            data = dict(service.data)

            # ent_ids is a generator, convert it to a list.
            data[ATTR_ENTITY_ID] = list(ent_ids)

            tasks.append(
                hass.services.async_call(
                    domain,
                    service.service,
                    data,
                    blocking=True,
                    context=service.context,
                )
            )

        if unsupported_entities:
            _LOGGER.warning(
                "The service homeassistant.%s does not support entities %s",
                service.service,
                ", ".join(sorted(unsupported_entities)),
            )

        if tasks:
            await asyncio.gather(*tasks)

    service_schema = vol.Schema({ATTR_ENTITY_ID: cv.entity_ids}, extra=vol.ALLOW_EXTRA)

    hass.services.async_register(
        ha.DOMAIN, SERVICE_TURN_OFF, async_handle_turn_service, schema=service_schema
    )
    hass.services.async_register(
        ha.DOMAIN, SERVICE_TURN_ON, async_handle_turn_service, schema=service_schema
    )
    hass.services.async_register(
        ha.DOMAIN, SERVICE_TOGGLE, async_handle_turn_service, schema=service_schema
    )

    async def async_handle_core_service(call):
        """Service handler for handling core services."""
        if call.service == SERVICE_HOMEASSISTANT_STOP:
            hass.async_create_task(hass.async_stop())
            return

        try:
            errors = await conf_util.async_check_ha_config_file(hass)
        except HomeAssistantError:
            return

        if errors:
            _LOGGER.error(errors)
            hass.components.persistent_notification.async_create(
                "Config error. See [the logs](/config/logs) for details.",
                "Config validating",
                f"{ha.DOMAIN}.check_config",
            )
            return

        if call.service == SERVICE_HOMEASSISTANT_RESTART:
            hass.async_create_task(hass.async_stop(RESTART_EXIT_CODE))

    async def async_handle_update_service(call):
        """Service handler for updating an entity."""
        if call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)

            if user is None:
                raise UnknownUser(
                    context=call.context,
                    permission=POLICY_CONTROL,
                    user_id=call.context.user_id,
                )

            for entity in call.data[ATTR_ENTITY_ID]:
                if not user.permissions.check_entity(entity, POLICY_CONTROL):
                    raise Unauthorized(
                        context=call.context,
                        permission=POLICY_CONTROL,
                        user_id=call.context.user_id,
                        perm_category=CAT_ENTITIES,
                    )

        tasks = [
            hass.helpers.entity_component.async_update_entity(entity)
            for entity in call.data[ATTR_ENTITY_ID]
        ]

        if tasks:
            await asyncio.wait(tasks)

    hass.helpers.service.async_register_admin_service(
        ha.DOMAIN, SERVICE_HOMEASSISTANT_STOP, async_handle_core_service
    )
    hass.helpers.service.async_register_admin_service(
        ha.DOMAIN, SERVICE_HOMEASSISTANT_RESTART, async_handle_core_service
    )
    hass.helpers.service.async_register_admin_service(
        ha.DOMAIN, SERVICE_CHECK_CONFIG, async_handle_core_service
    )
    hass.services.async_register(
        ha.DOMAIN,
        SERVICE_UPDATE_ENTITY,
        async_handle_update_service,
        schema=SCHEMA_UPDATE_ENTITY,
    )

    async def async_handle_reload_config(call):
        """Service handler for reloading core config."""
        try:
            conf = await conf_util.async_hass_config_yaml(hass)
        except HomeAssistantError as err:
            _LOGGER.error(err)
            return

        # auth only processed during startup
        await conf_util.async_process_ha_core_config(hass, conf.get(ha.DOMAIN) or {})

    hass.helpers.service.async_register_admin_service(
        ha.DOMAIN, SERVICE_RELOAD_CORE_CONFIG, async_handle_reload_config
    )

    async def async_set_location(call):
        """Service handler to set location."""
        await hass.config.async_update(
            latitude=call.data[ATTR_LATITUDE], longitude=call.data[ATTR_LONGITUDE]
        )

    hass.helpers.service.async_register_admin_service(
        ha.DOMAIN,
        SERVICE_SET_LOCATION,
        async_set_location,
        vol.Schema({ATTR_LATITUDE: cv.latitude, ATTR_LONGITUDE: cv.longitude}),
    )

    async def async_handle_reload_config_entry(call):
        """Service handler for reloading a config entry."""
        await hass.config_entries.async_reload(call.data[ATTR_CONFIG_ENTRY_ID])

    hass.helpers.service.async_register_admin_service(
        ha.DOMAIN,
        SERVICE_RELOAD_CONFIG_ENTRY,
        async_handle_reload_config_entry,
        schema=SCHEMA_RELOAD_CONFIG_ENTRY,
    )

    return True
