"""Support for RESTful binary sensors."""
from __future__ import annotations

import logging
import ssl
from xml.parsers.expat import ExpatError

from jsonpath import jsonpath
import voluptuous as vol
import xmltodict

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    PLATFORM_SCHEMA,
    BinarySensorEntity,
)
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_FORCE_UPDATE,
    CONF_RESOURCE,
    CONF_RESOURCE_TEMPLATE,
    CONF_UNIQUE_ID,
    CONF_VALUE_TEMPLATE,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.json import json_dumps, json_loads
from homeassistant.helpers.template import Template
from homeassistant.helpers.template_entity import TemplateEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import async_get_config_and_coordinator, create_rest_data_from_config
from .const import (
    CONF_JSON_ATTRS,
    CONF_JSON_ATTRS_PATH,
    DEFAULT_BINARY_SENSOR_NAME,
    XML_MIME_TYPES,
)
from .data import RestData
from .entity import RestEntity
from .schema import BINARY_SENSOR_SCHEMA, RESOURCE_SCHEMA

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({**RESOURCE_SCHEMA, **BINARY_SENSOR_SCHEMA})

PLATFORM_SCHEMA = vol.All(
    cv.has_at_least_one_key(CONF_RESOURCE, CONF_RESOURCE_TEMPLATE), PLATFORM_SCHEMA
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the REST binary sensor."""
    # Must update the sensor now (including fetching the rest resource) to
    # ensure it's updating its state.
    if discovery_info is not None:
        conf, coordinator, rest = await async_get_config_and_coordinator(
            hass, BINARY_SENSOR_DOMAIN, discovery_info
        )
    else:
        conf = config
        coordinator = None
        rest = create_rest_data_from_config(hass, conf)
        await rest.async_update(log_errors=False)

    if rest.data is None:
        if rest.last_exception:
            if isinstance(rest.last_exception, ssl.SSLError):
                _LOGGER.error(
                    "Error connecting %s failed with %s",
                    rest.url,
                    rest.last_exception,
                )
                return
            raise PlatformNotReady from rest.last_exception
        raise PlatformNotReady

    unique_id = conf.get(CONF_UNIQUE_ID)

    async_add_entities(
        [
            RestBinarySensor(
                hass,
                coordinator,
                rest,
                conf,
                unique_id,
            )
        ],
    )


class RestBinarySensor(RestEntity, TemplateEntity, BinarySensorEntity):
    """Representation of a REST binary sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator[None] | None,
        rest: RestData,
        config: ConfigType,
        unique_id: str | None,
    ) -> None:
        """Initialize a REST binary sensor."""
        RestEntity.__init__(
            self,
            coordinator,
            rest,
            config.get(CONF_RESOURCE_TEMPLATE),
            config[CONF_FORCE_UPDATE],
        )
        TemplateEntity.__init__(
            self,
            hass,
            config=config,
            fallback_name=DEFAULT_BINARY_SENSOR_NAME,
            unique_id=unique_id,
        )
        self._previous_data = None
        self._value_template: Template | None = config.get(CONF_VALUE_TEMPLATE)
        if (value_template := self._value_template) is not None:
            value_template.hass = hass
        self._json_attrs = config.get(CONF_JSON_ATTRS)
        self._json_attrs_path = config.get(CONF_JSON_ATTRS_PATH)

        self._attr_device_class = config.get(CONF_DEVICE_CLASS)

    def _update_from_rest_data(self) -> None:
        """Update state from the rest data."""
        response = self.rest.data
        _LOGGER.debug("Data fetched from resource: %s", response)

        if response is None:
            self._attr_is_on = False
            return

        if self.rest.headers is not None:
            # If the http request failed, headers will be None
            content_type = self.rest.headers.get("content-type")

            if content_type and content_type.startswith(XML_MIME_TYPES):
                try:
                    response = json_dumps(xmltodict.parse(response))
                    _LOGGER.debug("JSON converted from XML: %s", response)
                except ExpatError:
                    _LOGGER.debug(
                        "REST xml result could not be parsed and converted to JSON."
                        " Erroneous XML: %s",
                        response,
                    )

        if self._json_attrs:
            if response:
                try:
                    json_dict = json_loads(response)
                    if self._json_attrs_path is not None:
                        json_dict = jsonpath(json_dict, self._json_attrs_path)
                    # jsonpath will always store the result in json_dict[0]
                    # so the next line happens to work exactly as needed to
                    # find the result
                    if isinstance(json_dict, list):
                        json_dict = json_dict[0]
                    if isinstance(json_dict, dict):
                        self._attr_extra_state_attributes = {
                            k: json_dict[k] for k in self._json_attrs if k in json_dict
                        }
                    else:
                        _LOGGER.warning(
                            "JSON result was not a dictionary"
                            " or list with 0th element a dictionary"
                        )
                except ValueError:
                    _LOGGER.debug(
                        "REST result could not be parsed as JSON."
                        " Erroneous JSON: %s",
                        response,
                    )

            else:
                _LOGGER.debug("Empty reply found when expecting JSON data")

        if self._value_template is not None:
            response = self._value_template.async_render_with_possible_json_value(
                response, False
            )

        try:
            self._attr_is_on = bool(int(response))
        except ValueError:
            self._attr_is_on = {
                "true": True,
                "on": True,
                "open": True,
                "yes": True,
            }.get(response.lower(), False)
