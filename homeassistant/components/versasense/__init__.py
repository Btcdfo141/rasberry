"""Support for VersaSense MicroPnP devices."""
import logging

import pyversasense as pyv
import voluptuous as vol

from homeassistant.const import CONF_HOST
from homeassistant.helpers import aiohttp_client
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

from .const import PERIPHERAL_CLASS_SENSOR, PERIPHERAL_CLASS_SENSOR_ACTUATOR

_LOGGER = logging.getLogger(__name__)

DOMAIN = "versasense"

# Validation of the user's configuration
CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(CONF_HOST): cv.string})}, extra=vol.ALLOW_EXTRA
)


async def async_setup(hass, config):
    """Set up the versasense component."""
    session = aiohttp_client.async_get_clientsession(hass)
    consumer = pyv.Consumer(config[DOMAIN]["host"], session)

    hass.data[DOMAIN] = {"consumer": consumer}

    await _configure_entities(hass, config, consumer)

    # Return boolean to indicate that initialization was successful.
    return True


async def _configure_entities(hass, config, consumer):
    """Fetch all devices with their peripherals for representation."""
    devices = await consumer.fetchDevices()
    _LOGGER.debug(devices)

    sensor_info_list = []
    switch_info_list = []

    for mac, device in devices.items():
        _LOGGER.info("Device connected: %s %s", device.name, mac)

        for peripheral_id, peripheral in device.peripherals.items():
            hass.data[DOMAIN][peripheral_id] = peripheral

            if peripheral.classification == PERIPHERAL_CLASS_SENSOR:
                sensor_info_list = await _add_entity_info_to_list(
                    peripheral, device, sensor_info_list
                )
            elif peripheral.classification == PERIPHERAL_CLASS_SENSOR_ACTUATOR:
                switch_info_list = await _add_entity_info_to_list(
                    peripheral, device, switch_info_list
                )

    if sensor_info_list:
        await _load_platform(hass, config, "sensor", sensor_info_list)

    if switch_info_list:
        await _load_platform(hass, config, "switch", switch_info_list)


async def _add_entity_info_to_list(peripheral, device, entity_info_list):
    for measurement in peripheral.measurements:
        entity_info = {
            "identifier": peripheral.identifier,
            "unit": measurement.unit,
            "measurement": measurement.name,
            "parent_name": device.name,
        }

        entity_info_list.append(entity_info)

    return entity_info_list


async def _load_platform(hass, config, entity_type, entity_info_list):
    """Load platform with list of entity info."""
    hass.async_create_task(
        async_load_platform(hass, entity_type, DOMAIN, entity_info_list, config)
    )
