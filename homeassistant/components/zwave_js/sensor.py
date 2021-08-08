"""Representation of Z-Wave sensors."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Mapping, cast

import voluptuous as vol
from zwave_js_server.client import Client as ZwaveClient
from zwave_js_server.const import (
    CC_SPECIFIC_METER_TYPE,
    RESET_METER_OPTION_TARGET_VALUE,
    RESET_METER_OPTION_TYPE,
    CommandClass,
    ConfigurationValueType,
)
from zwave_js_server.model.node import Node as ZwaveNode
from zwave_js_server.model.value import ConfigurationValue

from homeassistant.components.sensor import (
    DEVICE_CLASS_BATTERY,
    ATTR_STATE_CLASS,
    DEVICE_CLASS_ENERGY,
    DOMAIN as SENSOR_DOMAIN,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, TEMP_CELSIUS, TEMP_FAHRENHEIT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_METER_TYPE,
    ATTR_METER_TYPE_NAME,
    ATTR_VALUE,
    DATA_CLIENT,
    DOMAIN,
    SERVICE_RESET_METER,
)
from .discovery import ZwaveDiscoveryInfo
from .entity import ZWaveBaseEntity
from .helpers import get_device_id

LOGGER = logging.getLogger(__name__)


@dataclass
class ZwaveSensorEntityDescription(SensorEntityDescription):
    """Base description of a Zwave Sensor entity."""

    info: ZwaveDiscoveryInfo | None = None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Z-Wave sensor from config entry."""
    client: ZwaveClient = hass.data[DOMAIN][config_entry.entry_id][DATA_CLIENT]

    @callback
    def async_add_sensor(info: ZwaveDiscoveryInfo) -> None:
        """Add Z-Wave Sensor."""
        entities: list[ZWaveBaseEntity] = []

        entity_description = ZwaveSensorEntityDescription(
            "sensor",
            device_class=info.platform_data.get(ATTR_DEVICE_CLASS),
            state_class=info.platform_data.get(ATTR_STATE_CLASS),
            info=info,
        )

        if info.platform_hint == "string_sensor":
            entities.append(ZWaveStringSensor(config_entry, client, entity_description))
        elif info.platform_hint == "numeric_sensor":
            entities.append(
                ZWaveNumericSensor(config_entry, client, entity_description)
            )
        elif info.platform_hint == "list_sensor":
            entities.append(ZWaveListSensor(config_entry, client, entity_description))
        elif info.platform_hint == "config_parameter":
            entities.append(
                ZWaveConfigParameterSensor(config_entry, client, entity_description)
            )
        elif info.platform_hint == "meter":
            entities.append(ZWaveMeterSensor(config_entry, client, entity_description))
        else:
            LOGGER.warning(
                "Sensor not implemented for %s/%s",
                info.platform_hint,
                info.primary_value.propertyname,
            )
            return

        async_add_entities(entities)

    @callback
    def async_add_node_status_sensor(node: ZwaveNode) -> None:
        """Add node status sensor."""
        async_add_entities([ZWaveNodeStatusSensor(config_entry, client, node)])

    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            f"{DOMAIN}_{config_entry.entry_id}_add_{SENSOR_DOMAIN}",
            async_add_sensor,
        )
    )

    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            f"{DOMAIN}_{config_entry.entry_id}_add_node_status_sensor",
            async_add_node_status_sensor,
        )
    )

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_RESET_METER,
        {
            vol.Optional(ATTR_METER_TYPE): vol.Coerce(int),
            vol.Optional(ATTR_VALUE): vol.Coerce(int),
        },
        "async_reset_meter",
    )


class ZwaveSensorBase(ZWaveBaseEntity, SensorEntity):
    """Basic Representation of a Z-Wave sensor."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        client: ZwaveClient,
        entity_description: ZwaveSensorEntityDescription,
    ) -> None:
        """Initialize a ZWaveSensorBase entity."""
        assert entity_description.info
        super().__init__(config_entry, client, entity_description.info)
        self.entity_description = entity_description

        # Entity class attributes
        self._attr_name = self.generate_name(include_value_name=True)


class ZWaveStringSensor(ZwaveSensorBase):
    """Representation of a Z-Wave String sensor."""

    @property
    def native_value(self) -> str | None:
        """Return state of the sensor."""
        if self.info.primary_value.value is None:
            return None
        return str(self.info.primary_value.value)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return unit of measurement the value is expressed in."""
        if self.info.primary_value.metadata.unit is None:
            return None
        return str(self.info.primary_value.metadata.unit)


class ZWaveNumericSensor(ZwaveSensorBase):
    """Representation of a Z-Wave Numeric sensor."""

    @property
    def native_value(self) -> float:
        """Return state of the sensor."""
        if self.info.primary_value.value is None:
            return 0
        return round(float(self.info.primary_value.value), 2)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return unit of measurement the value is expressed in."""
        if self.info.primary_value.metadata.unit is None:
            return None
        if self.info.primary_value.metadata.unit == "C":
            return TEMP_CELSIUS
        if self.info.primary_value.metadata.unit == "F":
            return TEMP_FAHRENHEIT

        return str(self.info.primary_value.metadata.unit)


class ZWaveMeterSensor(ZWaveNumericSensor):
    """Representation of a Z-Wave Meter CC sensor."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        client: ZwaveClient,
        entity_description: ZwaveSensorEntityDescription,
    ) -> None:
        """Initialize a ZWaveNumericSensor entity."""
        super().__init__(config_entry, client, entity_description)

        # Entity class attributes
        if self.device_class == DEVICE_CLASS_ENERGY:
            self._attr_state_class = STATE_CLASS_TOTAL_INCREASING
        else:
            self._attr_state_class = STATE_CLASS_MEASUREMENT

    @property
    def extra_state_attributes(self) -> Mapping[str, int | str] | None:
        """Return extra state attributes."""
        if meter_type := self.info.platform_data.get(ATTR_METER_TYPE):
            return {
                ATTR_METER_TYPE: meter_type.value,
                ATTR_METER_TYPE_NAME: meter_type.name.lower(),
            }
        return None

    async def async_reset_meter(
        self, meter_type: int | None = None, value: int | None = None
    ) -> None:
        """Reset meter(s) on device."""
        node = self.info.node
        primary_value = self.info.primary_value
        options = {}
        if meter_type is not None:
            options[RESET_METER_OPTION_TYPE] = meter_type
        if value is not None:
            options[RESET_METER_OPTION_TARGET_VALUE] = value
        args = [options] if options else []
        await node.endpoints[primary_value.endpoint].async_invoke_cc_api(
            CommandClass.METER, "reset", *args, wait_for_result=False
        )
        LOGGER.debug(
            "Meters on node %s endpoint %s reset with the following options: %s",
            node,
            primary_value.endpoint,
            options,
        )


class ZWaveListSensor(ZwaveSensorBase):
    """Representation of a Z-Wave Numeric sensor with multiple states."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        client: ZwaveClient,
        entity_description: ZwaveSensorEntityDescription,
    ) -> None:
        """Initialize a ZWaveListSensor entity."""
        super().__init__(config_entry, client, entity_description)

        # Entity class attributes
        self._attr_name = self.generate_name(
            include_value_name=True,
            alternate_value_name=self.info.primary_value.property_name,
            additional_info=[self.info.primary_value.property_key_name],
        )

    @property
    def native_value(self) -> str | None:
        """Return state of the sensor."""
        if self.info.primary_value.value is None:
            return None
        if (
            str(self.info.primary_value.value)
            not in self.info.primary_value.metadata.states
        ):
            return str(self.info.primary_value.value)
        return str(
            self.info.primary_value.metadata.states[str(self.info.primary_value.value)]
        )

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the device specific state attributes."""
        # add the value's int value as property for multi-value (list) items
        return {ATTR_VALUE: self.info.primary_value.value}


class ZWaveConfigParameterSensor(ZwaveSensorBase):
    """Representation of a Z-Wave config parameter sensor."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        client: ZwaveClient,
        entity_description: ZwaveSensorEntityDescription,
    ) -> None:
        """Initialize a ZWaveConfigParameterSensor entity."""
        super().__init__(config_entry, client, entity_description)
        self._primary_value = cast(ConfigurationValue, self.info.primary_value)

        # Entity class attributes
        self._attr_name = self.generate_name(
            include_value_name=True,
            alternate_value_name=self.info.primary_value.property_name,
            additional_info=[self.info.primary_value.property_key_name],
            name_suffix="Config Parameter",
        )

    @property
    def native_value(self) -> str | None:
        """Return state of the sensor."""
        if self.info.primary_value.value is None:
            return None
        if (
            self._primary_value.configuration_value_type == ConfigurationValueType.RANGE
            or (
                not str(self.info.primary_value.value)
                in self.info.primary_value.metadata.states
            )
        ):
            return str(self.info.primary_value.value)
        return str(
            self.info.primary_value.metadata.states[str(self.info.primary_value.value)]
        )

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the device specific state attributes."""
        if self._primary_value.configuration_value_type == ConfigurationValueType.RANGE:
            return None
        # add the value's int value as property for multi-value (list) items
        return {ATTR_VALUE: self.info.primary_value.value}


class ZWaveNodeStatusSensor(SensorEntity):
    """Representation of a node status sensor."""

    _attr_should_poll = False
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, config_entry: ConfigEntry, client: ZwaveClient, node: ZwaveNode
    ) -> None:
        """Initialize a generic Z-Wave device entity."""
        self.config_entry = config_entry
        self.client = client
        self.node = node
        name: str = (
            self.node.name
            or self.node.device_config.description
            or f"Node {self.node.node_id}"
        )
        # Entity class attributes
        self._attr_name = f"{name}: Node Status"
        self._attr_unique_id = (
            f"{self.client.driver.controller.home_id}.{node.node_id}.node_status"
        )
        # device is precreated in main handler
        self._attr_device_info = {
            "identifiers": {get_device_id(self.client, self.node)},
        }
        self._attr_native_value: str = node.status.name.lower()

    async def async_poll_value(self, _: bool) -> None:
        """Poll a value."""
        raise ValueError("There is no value to poll for this entity")

    def _status_changed(self, _: dict) -> None:
        """Call when status event is received."""
        self._attr_native_value = self.node.status.name.lower()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Call when entity is added."""
        # Add value_changed callbacks.
        for evt in ("wake up", "sleep", "dead", "alive"):
            self.async_on_remove(self.node.on(evt, self._status_changed))
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self.unique_id}_poll_value",
                self.async_poll_value,
            )
        )
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return self.client.connected and bool(self.node.ready)
