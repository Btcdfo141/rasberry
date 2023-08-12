"""Platform for Sungrow Solar sensors."""
from enum import Enum
import logging

from pysungrow.definitions.device import SungrowDevice

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SungrowCoordinatorEntity, SungrowData
from .const import BATTERY_DEVICE_VARIABLES, DOMAIN

_LOGGER = logging.getLogger(__name__)


DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="protocol_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="protocol_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="arm_software_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="dsp_software_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="serial_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="device_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="nominal_output_power",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="output_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(key="daily_output_energy"),
    SensorEntityDescription(key="total_output_energy"),
    SensorEntityDescription(
        key="total_running_time",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="internal_temperature", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="mppt_1_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel",
    ),
    SensorEntityDescription(
        key="mppt_2_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel",
    ),
    SensorEntityDescription(
        key="dc_1_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel",
    ),
    SensorEntityDescription(
        key="dc_2_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel",
    ),
    SensorEntityDescription(
        key="dc_3_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel",
    ),
    SensorEntityDescription(
        key="dc_4_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel",
    ),
    SensorEntityDescription(
        key="mppt_1_current",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel",
    ),
    SensorEntityDescription(
        key="mppt_2_current",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel",
    ),
    SensorEntityDescription(
        key="dc_1_current",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel",
    ),
    SensorEntityDescription(
        key="dc_2_current",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel",
    ),
    SensorEntityDescription(
        key="dc_3_current",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel",
    ),
    SensorEntityDescription(
        key="dc_4_current",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel",
    ),
    SensorEntityDescription(
        key="total_dc_power",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:solar-panel-large",
    ),
    SensorEntityDescription(
        key="phase_a_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:transmission-tower",
    ),
    SensorEntityDescription(
        key="phase_b_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:transmission-tower",
    ),
    SensorEntityDescription(
        key="phase_c_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:transmission-tower",
    ),
    SensorEntityDescription(
        key="line_ab_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:transmission-tower",
    ),
    SensorEntityDescription(
        key="line_bc_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:transmission-tower",
    ),
    SensorEntityDescription(
        key="line_ca_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:transmission-tower",
    ),
    SensorEntityDescription(
        key="phase_a_current", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="phase_b_current", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="phase_c_current", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="total_active_power", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="reactive_power", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="grid_frequency",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:transmission-tower",
    ),
    SensorEntityDescription(key="daily_pv_generation", icon="mdi:solar-power-variant"),
    SensorEntityDescription(key="total_pv_generation", icon="mdi:solar-power-variant"),
    SensorEntityDescription(key="daily_export_from_pv", icon="mdi:solar-power-variant"),
    SensorEntityDescription(key="total_export_from_pv", icon="mdi:solar-power-variant"),
    SensorEntityDescription(
        key="load_power", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="export_power", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="daily_battery_charge_energy_from_pv", icon="mdi:solar-power-variant"
    ),
    SensorEntityDescription(
        key="total_battery_charge_energy_from_pv", icon="mdi:solar-power-variant"
    ),
    SensorEntityDescription(
        key="co2_reduction",
        entity_registry_enabled_default=False,
        icon="mdi:molecule-co2",
        name="CO₂ reduction",
    ),
    SensorEntityDescription(
        key="daily_direct_energy_consumption", icon="mdi:home-lightning-bolt"
    ),
    SensorEntityDescription(
        key="total_direct_energy_consumption", icon="mdi:home-lightning-bolt"
    ),
    SensorEntityDescription(
        key="battery_voltage", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="battery_current", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="battery_power", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="battery_level", device_class=SensorDeviceClass.BATTERY
    ),
    SensorEntityDescription(
        key="battery_health",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery-heart",
    ),
    SensorEntityDescription(
        key="battery_temperature", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(key="daily_battery_discharge_energy"),
    SensorEntityDescription(key="total_battery_discharge_energy"),
    SensorEntityDescription(
        key="daily_self_consumption", icon="mdi:home-lightning-bolt"
    ),
    SensorEntityDescription(
        key="daily_import_energy", icon="mdi:transmission-tower-export"
    ),
    SensorEntityDescription(
        key="total_import_energy", icon="mdi:transmission-tower-export"
    ),
    SensorEntityDescription(key="daily_charge_energy", icon="mdi:battery-charging"),
    SensorEntityDescription(key="total_charge_energy", icon="mdi:battery-charging"),
    SensorEntityDescription(
        key="drm_state",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="daily_export_energy", icon="mdi:transmission-tower-import"
    ),
    SensorEntityDescription(
        key="total_export_energy", icon="mdi:transmission-tower-import"
    ),
    SensorEntityDescription(key="battery_maintenance"),
    SensorEntityDescription(
        key="battery_type",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="battery_nominal_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="battery_capacity",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="battery_over_voltage_threshold",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="battery_under_voltage_threshold",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="battery_over_temperature_threshold",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        icon="mdi:temperature-alert",
    ),
    SensorEntityDescription(
        key="battery_under_temperature_threshold",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        icon="mdi:temperature-alert",
    ),
    SensorEntityDescription(
        key="grid_frequency_fine",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:transmission-tower",
    ),
    SensorEntityDescription(
        key="work_state", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="fault_date", entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:alert"
    ),
    SensorEntityDescription(
        key="fault_code", entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:alert"
    ),
    SensorEntityDescription(
        key="nominal_reactive_output_power",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="impedance_to_ground",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="daily_running_time",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="country",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:earth",
    ),
    SensorEntityDescription(
        key="monthly_power_yield", entity_registry_enabled_default=False
    ),
    SensorEntityDescription(
        key="negative_voltage_to_ground",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="bus_voltage",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="power_factor_setting",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="reactive_power_adjustment",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="reactive_power_adjustment_switch",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="reactive_power_percentage",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add solarlog entry."""
    coordinator: SungrowData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SungrowSensor(
            coordinator,
            coordinator.battery_info
            if description.key in BATTERY_DEVICE_VARIABLES
            else coordinator.device_info,
            description,
        )
        for description in DESCRIPTIONS
        if description.key in coordinator.client.keys
    )


class SungrowSensor(SungrowCoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    def __init__(
        self,
        coordinator: SungrowData,
        device_info: DeviceInfo,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_info, description)
        key = description.key

        # set entity metadata based on variable metadata
        variable = self.variable
        self._attr_native_unit_of_measurement = variable.unit
        if (
            key.startswith("total_")
            or key.startswith("daily_")
            or key.startswith("monthly_")
        ) and variable.unit == "kWh":
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif variable.unit is not None:
            self._attr_state_class = SensorStateClass.MEASUREMENT

        if (
            key.startswith("total_")
            and coordinator.client.variable(key.replace("total_", "daily_")) is not None
        ):
            # prefer daily sensors rather than total in the UI
            self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self):
        """Return the native sensor value."""
        value = self.data
        if isinstance(value, Enum):
            return value.name.lower()
        if isinstance(value, SungrowDevice):
            return value.name
        return value
