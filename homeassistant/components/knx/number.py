"""Support for KNX/IP numeric values."""
from __future__ import annotations

from typing import cast

from xknx import XKNX
from xknx.devices import NumericValue

from homeassistant.components.number import NumberEntity
from homeassistant.const import CONF_NAME, CONF_TYPE, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_RESPOND_TO_READ, CONF_STATE_ADDRESS, DOMAIN, KNX_ADDRESS
from .knx_entity import KnxEntity
from .schema import NumberSchema


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up number entities for KNX platform."""
    if not discovery_info or not discovery_info["platform_config"]:
        return

    platform_config = discovery_info["platform_config"]
    xknx: XKNX = hass.data[DOMAIN].xknx

    entities = []
    for entity_config in platform_config:
        entities.append(KNXNumber(xknx, entity_config))

    async_add_entities(entities)


def _create_expose_sensor(xknx: XKNX, config: ConfigType) -> NumericValue:
    """Return a KNX NumericValue to be used within XKNX."""
    return NumericValue(
        xknx,
        name=config[CONF_NAME],
        group_address=config[KNX_ADDRESS],
        group_address_state=config.get(CONF_STATE_ADDRESS),
        respond_to_read=config[CONF_RESPOND_TO_READ],
        value_type=config[CONF_TYPE],
    )


class KNXNumber(KnxEntity, NumberEntity, RestoreEntity):
    """Representation of a KNX number."""

    def __init__(self, xknx: XKNX, config: ConfigType) -> None:
        """Initialize a KNX number."""
        self._device: NumericValue
        super().__init__(_create_expose_sensor(xknx, config))
        self._unique_id = f"{self._device.sensor_value.group_address}"

        self._attr_min_value = config.get(
            NumberSchema.CONF_MIN,
            self._device.sensor_value.dpt_class.value_min,
        )
        self._attr_max_value = config.get(
            NumberSchema.CONF_MAX,
            self._device.sensor_value.dpt_class.value_max,
        )
        self._attr_step = config.get(
            NumberSchema.CONF_STEP,
            self._device.sensor_value.dpt_class.resolution,
        )
        self._device.sensor_value.value = max(0, self.min_value)

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        if not self._device.sensor_value.readable and (
            last_state := await self.async_get_last_state()
        ):
            if last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                self._device.sensor_value.value = float(last_state.state)

    @property
    def value(self) -> float:
        """Return the entity value to represent the entity state."""
        # self._device.sensor_value.value is set in __init__ so it is never None
        return cast(float, self._device.resolve_state())

    async def async_set_value(self, value: float) -> None:
        """Set new value."""
        if value < self.min_value or value > self.max_value:
            raise ValueError(
                f"Invalid value for {self.entity_id}: {value} "
                f"(range {self.min_value} - {self.max_value})"
            )
        await self._device.set(value)
