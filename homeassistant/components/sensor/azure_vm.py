"""
Sensor platform representing a Azure Virtual Machine.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/sensor.azure_vm/
"""

from datetime import timedelta
import asyncio
import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.components.azure_cloud import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['azure_cloud']
REQUIREMENTS = ['azure-mgmt-compute==2.0.0']

CONF_NAME = 'name'
CONG_RESOURCE_GROUP = 'resource_group'

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONG_RESOURCE_GROUP): cv.string,
})


@asyncio.coroutine
async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Add the azure vm sensor."""
    async_add_entities([AzureVmSensor(hass, config)])


class AzureVmSensor(Entity):
    """Representation of an Azure virutal machine."""

    def __init__(self, hass, config):
        """Initialize the sensor."""
        from azure.mgmt.compute import ComputeManagementClient

        self._azure_compute_client = ComputeManagementClient(
            hass.data[DOMAIN].credentials, hass.data[DOMAIN].subscription_id)
        self._name = config.get(CONF_NAME)
        self._resource_group = config.get(CONG_RESOURCE_GROUP)
        self._state = None

    @property
    def name(self):
        """Return the name of the azure vm."""
        return self._name

    @property
    def state(self):
        """Return the state of the azure vm."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend."""
        if self._state == "VM running":
            return 'mdi:server'
        return 'mdi:server-off'

    @asyncio.coroutine
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Retrieve latest state."""
        virtual_machine = self._azure_compute_client.virtual_machines.get(
            self._resource_group, self._name, expand='instanceView')
        _LOGGER.debug("Status of azure vm %s is %s ", self._name,
                      virtual_machine.instance_view.statuses[1].display_status)
        self._state = virtual_machine.instance_view.statuses[1].display_status
