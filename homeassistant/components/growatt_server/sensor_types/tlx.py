"""
Growatt Sensor definitions for the TLX type.

TLX Type is also shown on the UI as: "MIN/MIC/MOD/NEO"
"""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    TEMP_CELSIUS,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
)

from .sensor_entity_description import GrowattSensorEntityDescription

TLX_SENSOR_TYPES: tuple[GrowattSensorEntityDescription, ...] = (
    GrowattSensorEntityDescription(
        key="tlx_energy_today",
        name="Energy today",
        api_key="eacToday",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_energy_total",
        name="Lifetime energy output",
        api_key="eacTotal",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=1,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_energy_total_input_1",
        name="Lifetime total energy input 1",
        api_key="epv1Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=1,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_energy_today_input_1",
        name="Energy Today Input 1",
        api_key="epv1Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_voltage_input_1",
        name="Input 1 voltage",
        api_key="vpv1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_amperage_input_1",
        name="Input 1 Amperage",
        api_key="ipv1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_wattage_input_1",
        name="Input 1 Wattage",
        api_key="ppv1",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_energy_total_input_2",
        name="Lifetime total energy input 2",
        api_key="epv2Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=1,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_energy_today_input_2",
        name="Energy Today Input 2",
        api_key="epv2Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_voltage_input_2",
        name="Input 2 voltage",
        api_key="vpv2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_amperage_input_2",
        name="Input 2 Amperage",
        api_key="ipv2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_wattage_input_2",
        name="Input 2 Wattage",
        api_key="ppv2",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_energy_total_input_3",
        name="Lifetime total energy input 3",
        api_key="epv3Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=1,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_energy_today_input_3",
        name="Energy Today Input 3",
        api_key="epv3Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_voltage_input_3",
        name="Input 3 voltage",
        api_key="vpv3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_amperage_input_3",
        name="Input 3 Amperage",
        api_key="ipv3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_wattage_input_3",
        name="Input 3 Wattage",
        api_key="ppv3",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_energy_total_input_4",
        name="Lifetime total energy input 4",
        api_key="epv4Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=1,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_energy_today_input_4",
        name="Energy Today Input 4",
        api_key="epv4Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_voltage_input_4",
        name="Input 4 voltage",
        api_key="vpv4",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_amperage_input_4",
        name="Input 4 Amperage",
        api_key="ipv4",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_wattage_input_4",
        name="Input 4 Wattage",
        api_key="ppv4",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_solar_generation_total",
        name="Lifetime total solar energy",
        api_key="epvTotal",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_internal_wattage",
        name="Internal wattage",
        api_key="ppv",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_reactive_voltage",
        name="Reactive voltage",
        api_key="vacrs",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_frequency",
        name="AC frequency",
        api_key="fac",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_current_wattage",
        name="Output power",
        api_key="pac",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_temperature_1",
        name="Temperature 1",
        api_key="temp1",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_temperature_2",
        name="Temperature 2",
        api_key="temp2",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_temperature_3",
        name="Temperature 3",
        api_key="temp3",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_temperature_4",
        name="Temperature 4",
        api_key="temp4",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_temperature_5",
        name="Temperature 5",
        api_key="temp5",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        precision=1,
    ),
    GrowattSensorEntityDescription(
        key="tlx_all_batteries_discharge_today",
        name="All batteries discharged today",
        api_key="edischargeToday",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GrowattSensorEntityDescription(
        key="tlx_all_batteries_discharge_total",
        name="Lifetime total all batteries discharged",
        api_key="edischargeTotal",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_battery_1_discharge_w",
        name="Battery 1 discharging W",
        api_key="bdc1DischargePower",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    GrowattSensorEntityDescription(
        key="tlx_battery_1_discharge_total",
        name="Lifetime total battery 1 discharged",
        api_key="bdc1DischargeTotal",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_battery_2_discharge_w",
        name="Battery 2 discharging W",
        api_key="bdc1DischargePower",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    GrowattSensorEntityDescription(
        key="tlx_battery_2_discharge_total",
        name="Lifetime total battery 2 discharged",
        api_key="bdc1DischargeTotal",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_all_batteries_charge_today",
        name="All batteries charged today",
        api_key="echargeToday",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GrowattSensorEntityDescription(
        key="tlx_all_batteries_charge_total",
        name="Lifetime total all batteries charged",
        api_key="echargeTotal",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_battery_1_charge_w",
        name="Battery 1 charging W",
        api_key="bdc1ChargePower",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    GrowattSensorEntityDescription(
        key="tlx_battery_1_charge_total",
        name="Lifetime total battery 1 charged",
        api_key="bdc1ChargeTotal",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_battery_2_charge_w",
        name="Battery 2 charging W",
        api_key="bdc1ChargePower",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    GrowattSensorEntityDescription(
        key="tlx_battery_2_charge_total",
        name="Lifetime total battery 2 charged",
        api_key="bdc1ChargeTotal",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_export_to_grid_today",
        name="Export to grid today",
        api_key="etoGridToday",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GrowattSensorEntityDescription(
        key="tlx_export_to_grid_total",
        name="Lifetime total export to grid",
        api_key="etoGridTotal",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_load_consumption_today",
        name="Load consumption today",
        api_key="elocalLoadToday",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GrowattSensorEntityDescription(
        key="mix_load_consumption_total",
        name="Lifetime total load consumption",
        api_key="elocalLoadTotal",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        never_resets=True,
    ),
    GrowattSensorEntityDescription(
        key="tlx_statement_of_charge",
        name="Statement of charge (SoC)",
        api_key="bmsSoc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
    ),
)
