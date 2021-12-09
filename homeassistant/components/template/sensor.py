"""Allows the creation of a sensor that breaks out state_attributes."""
from __future__ import annotations

from datetime import date, datetime
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import (
    CONF_STATE_CLASS,
    DEVICE_CLASSES_SCHEMA,
    DOMAIN as SENSOR_DOMAIN,
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    STATE_CLASSES_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_DEVICE_CLASS,
    CONF_ENTITY_PICTURE_TEMPLATE,
    CONF_FRIENDLY_NAME,
    CONF_FRIENDLY_NAME_TEMPLATE,
    CONF_ICON_TEMPLATE,
    CONF_NAME,
    CONF_SENSORS,
    CONF_STATE,
    CONF_UNIQUE_ID,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_VALUE_TEMPLATE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import config_validation as cv, template
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ATTRIBUTE_TEMPLATES,
    CONF_AVAILABILITY_TEMPLATE,
    CONF_OBJECT_ID,
    CONF_TRIGGER,
)
from .template_entity import (
    TEMPLATE_ENTITY_COMMON_SCHEMA,
    TemplateEntity,
    rewrite_common_legacy_to_modern_conf,
)
from .trigger_entity import TriggerEntity

LEGACY_FIELDS = {
    CONF_FRIENDLY_NAME_TEMPLATE: CONF_NAME,
    CONF_FRIENDLY_NAME: CONF_NAME,
    CONF_VALUE_TEMPLATE: CONF_STATE,
}


SENSOR_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        vol.Optional(CONF_NAME): cv.template,
        vol.Optional(CONF_STATE_CLASS): STATE_CLASSES_SCHEMA,
        vol.Required(CONF_STATE): cv.template,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    }
).extend(TEMPLATE_ENTITY_COMMON_SCHEMA.schema)


LEGACY_SENSOR_SCHEMA = vol.All(
    cv.deprecated(ATTR_ENTITY_ID),
    vol.Schema(
        {
            vol.Required(CONF_VALUE_TEMPLATE): cv.template,
            vol.Optional(CONF_ICON_TEMPLATE): cv.template,
            vol.Optional(CONF_ENTITY_PICTURE_TEMPLATE): cv.template,
            vol.Optional(CONF_FRIENDLY_NAME_TEMPLATE): cv.template,
            vol.Optional(CONF_AVAILABILITY_TEMPLATE): cv.template,
            vol.Optional(CONF_ATTRIBUTE_TEMPLATES, default={}): vol.Schema(
                {cv.string: cv.template}
            ),
            vol.Optional(CONF_FRIENDLY_NAME): cv.string,
            vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
            vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
            vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
            vol.Optional(CONF_UNIQUE_ID): cv.string,
        }
    ),
)
_LOGGER = logging.getLogger(__name__)


def extra_validation_checks(val):
    """Run extra validation checks."""
    if CONF_TRIGGER in val:
        raise vol.Invalid(
            "You can only add triggers to template entities if they are defined under `template:`. "
            "See the template documentation for more information: https://www.home-assistant.io/integrations/template/"
        )

    if CONF_SENSORS not in val and SENSOR_DOMAIN not in val:
        raise vol.Invalid(f"Required key {SENSOR_DOMAIN} not defined")

    return val


def rewrite_legacy_to_modern_conf(cfg: dict[str, dict]) -> list[dict]:
    """Rewrite legacy sensor definitions to modern ones."""
    sensors = []

    for object_id, entity_cfg in cfg.items():
        entity_cfg = {**entity_cfg, CONF_OBJECT_ID: object_id}

        entity_cfg = rewrite_common_legacy_to_modern_conf(entity_cfg, LEGACY_FIELDS)

        if CONF_NAME not in entity_cfg:
            entity_cfg[CONF_NAME] = template.Template(object_id)

        sensors.append(entity_cfg)

    return sensors


PLATFORM_SCHEMA = vol.All(
    PLATFORM_SCHEMA.extend(
        {
            vol.Optional(CONF_TRIGGER): cv.match_all,  # to raise custom warning
            vol.Required(CONF_SENSORS): cv.schema_with_slug_keys(LEGACY_SENSOR_SCHEMA),
        }
    ),
    extra_validation_checks,
)


@callback
def _async_create_template_tracking_entities(
    async_add_entities, hass, definitions: list[dict], unique_id_prefix: str | None
):
    """Create the template sensors."""
    sensors = []

    for entity_conf in definitions:
        unique_id = entity_conf.get(CONF_UNIQUE_ID)

        if unique_id and unique_id_prefix:
            unique_id = f"{unique_id_prefix}-{unique_id}"

        sensors.append(
            SensorTemplate(
                hass,
                entity_conf,
                unique_id,
            )
        )

    async_add_entities(sensors)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the template sensors."""
    if discovery_info is None:
        _async_create_template_tracking_entities(
            async_add_entities,
            hass,
            rewrite_legacy_to_modern_conf(config[CONF_SENSORS]),
            None,
        )
        return

    if "coordinator" in discovery_info:
        async_add_entities(
            TriggerSensorEntity(hass, discovery_info["coordinator"], config)
            for config in discovery_info["entities"]
        )
        return

    _async_create_template_tracking_entities(
        async_add_entities,
        hass,
        discovery_info["entities"],
        discovery_info["unique_id"],
    )


class SensorTemplate(TemplateEntity, SensorEntity):
    """Representation of a Template Sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
        unique_id: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(config=config)
        if (object_id := config.get(CONF_OBJECT_ID)) is not None:
            self.entity_id = async_generate_entity_id(
                ENTITY_ID_FORMAT, object_id, hass=hass
            )

        self._friendly_name_template = config.get(CONF_NAME)

        self._attr_name = None
        # Try to render the name as it can influence the entity ID
        if self._friendly_name_template:
            self._friendly_name_template.hass = hass
            try:
                self._attr_name = self._friendly_name_template.async_render(
                    parse_result=False
                )
            except template.TemplateError:
                pass

        self._attr_native_unit_of_measurement = config.get(CONF_UNIT_OF_MEASUREMENT)
        self._template = config.get(CONF_STATE)
        self._attr_device_class = config.get(CONF_DEVICE_CLASS)
        self._attr_state_class = config.get(CONF_STATE_CLASS)
        self._attr_unique_id = unique_id

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.add_template_attribute(
            "_attr_native_value", self._template, None, self._update_state
        )
        if self._friendly_name_template and not self._friendly_name_template.is_static:
            self.add_template_attribute("_attr_name", self._friendly_name_template)

        await super().async_added_to_hass()

    @callback
    def _update_state(self, result):
        super()._update_state(result)
        if isinstance(result, TemplateError):
            self._attr_native_value = None
            return

        if result is None or self.device_class not in (
            SensorDeviceClass.DATE,
            SensorDeviceClass.TIMESTAMP,
        ):
            self._attr_native_value = result
            return

        if self.device_class == SensorDeviceClass.TIMESTAMP:
            if (parsed_timestamp := dt_util.parse_datetime(result)) is None:
                _LOGGER.warning(
                    "%s rendered invalid timestamp: %s", self.entity_id, result
                )
                self._attr_native_value = None
                return

            if parsed_timestamp.tzinfo is None:
                _LOGGER.warning(
                    "%s rendered timestamp without timezone: %s", self.entity_id, result
                )
                self._attr_native_value = None
                return

            self._attr_native_value = parsed_timestamp
            return

        # Date device class
        parsed_date = dt_util.parse_date(result)

        if parsed_date is not None:
            self._attr_native_value = parsed_date
            return

        _LOGGER.warning("%s rendered invalid date %s", self.entity_id, result)
        self._attr_native_value = None


class TriggerSensorEntity(TriggerEntity, SensorEntity):
    """Sensor entity based on trigger data."""

    domain = SENSOR_DOMAIN
    extra_template_keys = (CONF_STATE,)

    @property
    def native_value(self) -> str | datetime | date | None:
        """Return state of the sensor."""
        return self._rendered.get(CONF_STATE)

    @property
    def state_class(self) -> str | None:
        """Sensor state class."""
        return self._config.get(CONF_STATE_CLASS)

    @callback
    def _process_data(self) -> None:
        """Process new data."""
        super()._process_data()

        if (
            state := self._rendered.get(CONF_STATE)
        ) is None or self.device_class not in (
            SensorDeviceClass.DATE,
            SensorDeviceClass.TIMESTAMP,
        ):
            return

        if self.device_class == SensorDeviceClass.TIMESTAMP:
            if (parsed_timestamp := dt_util.parse_datetime(state)) is None:
                _LOGGER.warning(
                    "%s rendered invalid timestamp: %s", self.entity_id, state
                )
                self._rendered[CONF_STATE] = None
                return

            if parsed_timestamp.tzinfo is None:
                _LOGGER.warning(
                    "%s rendered timestamp without timezone: %s", self.entity_id, state
                )
                self._rendered[CONF_STATE] = None
                return

            self._rendered[CONF_STATE] = parsed_timestamp
            return

        # Date device class
        parsed_date = dt_util.parse_date(state)

        if parsed_date is not None:
            self._rendered[CONF_STATE] = parsed_date
            return

        _LOGGER.warning("%s rendered invalid date %s", self.entity_id, state)
        self._rendered[CONF_STATE] = None
