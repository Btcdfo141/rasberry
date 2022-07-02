"""The scrape component."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components.rest.data import RestData

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.rest import RESOURCE_SCHEMA, create_rest_data_from_config
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_AUTHENTICATION,
    CONF_HEADERS,
    CONF_PASSWORD,
    CONF_RESOURCE,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VALUE_TEMPLATE,
    CONF_VERIFY_SSL,
    HTTP_DIGEST_AUTHENTICATION,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.template_entity import TEMPLATE_SENSOR_BASE_SCHEMA
from homeassistant.helpers.typing import ConfigType

from .const import CONF_INDEX, CONF_SELECT, DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS
from .coordinator import ScrapeCoordinator

SENSOR_SCHEMA = vol.Schema(
    {
        **TEMPLATE_SENSOR_BASE_SCHEMA.schema,
        vol.Optional(CONF_ATTRIBUTE): cv.string,
        vol.Optional(CONF_INDEX, default=0): cv.positive_int,
        vol.Required(CONF_SELECT): cv.string,
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    }
)

COMBINED_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SCAN_INTERVAL): cv.time_period,
        **RESOURCE_SCHEMA,
        vol.Optional(SENSOR_DOMAIN): vol.All(
            cv.ensure_list, [vol.Schema(SENSOR_SCHEMA)]
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(DOMAIN): vol.All(cv.ensure_list, [COMBINED_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Scrape from yaml config."""
    scrape_config: list[ConfigType] | None
    if not (scrape_config := config.get(DOMAIN)):
        return True

    load_coroutines: list[Coroutine[Any, Any, None]] = []
    for resource_config in scrape_config:
        rest = create_rest_data_from_config(hass, resource_config)
        scan_interval: timedelta = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        coordinator = ScrapeCoordinator(hass, rest, scan_interval)

        sensors: list[ConfigType] = resource_config.get(SENSOR_DOMAIN, [])
        if sensors:
            load_coroutines.append(
                discovery.async_load_platform(
                    hass,
                    Platform.SENSOR,
                    DOMAIN,
                    {"coordinator": coordinator, "configs": sensors},
                    config,
                )
            )

    if load_coroutines:
        await asyncio.gather(*load_coroutines)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Scrape from a config entry."""

    resource: str = entry.options[CONF_RESOURCE]
    method: str = "GET"
    payload: str | None = None
    headers: str | None = entry.options.get(CONF_HEADERS)
    verify_ssl: bool = entry.options[CONF_VERIFY_SSL]
    username: str | None = entry.options.get(CONF_USERNAME)
    password: str | None = entry.options.get(CONF_PASSWORD)
    authentication = entry.options.get(CONF_AUTHENTICATION)

    rest = await load_rest_data(
        hass,
        resource,
        method,
        payload,
        headers,
        verify_ssl,
        username,
        password,
        authentication,
    )

    if rest.data is None:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = rest

    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def load_rest_data(
    hass: HomeAssistant,
    resource: str,
    method: str,
    payload: str | None,
    headers: str | None,
    verify_ssl: bool,
    username: str | None,
    password: str | None,
    authentication: str | None,
) -> RestData:
    """Load rest data."""

    auth: httpx.DigestAuth | tuple[str, str] | None = None
    if username and password:
        if authentication == HTTP_DIGEST_AUTHENTICATION:
            auth = httpx.DigestAuth(username, password)
        else:
            auth = (username, password)

    rest = RestData(hass, method, resource, auth, headers, None, payload, verify_ssl)
    await rest.async_update()

    return rest


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener for options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Scrape config entry."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
