"""The ViCare integration."""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
import logging
import os
from typing import Any

from PyViCare.PyViCare import PyViCare
from PyViCare.PyViCareUtils import (
    PyViCareInvalidConfigurationError,
    PyViCareInvalidCredentialsError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import STORAGE_DIR

from .const import DEFAULT_CACHE_DURATION, DEVICE_CONFIG_LIST, DOMAIN, PLATFORMS
from .utils import get_device

_LOGGER = logging.getLogger(__name__)
_TOKEN_FILENAME = "vicare_token.save"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from config entry."""
    _LOGGER.debug("Setting up ViCare component")

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = {}

    try:
        await hass.async_add_executor_job(setup_vicare_api, hass, entry)
    except (PyViCareInvalidConfigurationError, PyViCareInvalidCredentialsError) as err:
        raise ConfigEntryAuthFailed("Authentication failed") from err

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


def vicare_login(
    hass: HomeAssistant,
    entry_data: Mapping[str, Any],
    cache_duration=DEFAULT_CACHE_DURATION,
) -> PyViCare:
    """Login via PyVicare API."""
    vicare_api = PyViCare()
    vicare_api.setCacheDuration(cache_duration)
    vicare_api.initWithCredentials(
        entry_data[CONF_USERNAME],
        entry_data[CONF_PASSWORD],
        entry_data[CONF_CLIENT_ID],
        hass.config.path(STORAGE_DIR, _TOKEN_FILENAME),
    )
    return vicare_api


def setup_vicare_api(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up PyVicare API."""
    vicare_api = vicare_login(hass, entry.data)

    number_of_devices = len(vicare_api.devices)
    if number_of_devices > 1:
        cache_duration = max(
            DEFAULT_CACHE_DURATION, DEFAULT_CACHE_DURATION * number_of_devices
        )
        _LOGGER.info(
            "Found %s devices, adjusting cache duration to %s",
            number_of_devices,
            cache_duration,
        )
        vicare_api = vicare_login(hass, entry.data, cache_duration)

    device_config_list = vicare_api.devices
    for device in device_config_list:
        _LOGGER.info(
            "Found device: %s (online: %s)", device.getModel(), str(device.isOnline())
        )

    hass.data[DOMAIN][entry.entry_id][DEVICE_CONFIG_LIST] = [
        (device_config, get_device(entry, device_config))
        for device_config in device_config_list
    ]


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload ViCare config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    with suppress(FileNotFoundError):
        await hass.async_add_executor_job(
            os.remove, hass.config.path(STORAGE_DIR, _TOKEN_FILENAME)
        )

    return unload_ok
