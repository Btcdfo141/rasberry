"""Constants for Nettigo Air Monitor integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ICON,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_SIGNAL_STRENGTH,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_TIMESTAMP,
    PERCENTAGE,
    PRESSURE_HPA,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    TEMP_CELSIUS,
)

from .model import SensorDescription

ATTR_BME280_HUMIDITY: Final = "bme280_humidity"
ATTR_BME280_PRESSURE: Final = "bme280_pressure"
ATTR_BME280_TEMPERATURE: Final = "bme280_temperature"
ATTR_BMP280_PRESSURE: Final = "bmp280_pressure"
ATTR_BMP280_TEMPERATURE: Final = "bmp280_temperature"
ATTR_DHT22_HUMIDITY: Final = "humidity"
ATTR_DHT22_TEMPERATURE: Final = "temperature"
ATTR_HECA_HUMIDITY: Final = "heca_humidity"
ATTR_HECA_TEMPERATURE: Final = "heca_temperature"
ATTR_MHZ14A_CARBON_DIOXIDE: Final = "conc_co2_ppm"
ATTR_SHT3X_HUMIDITY: Final = "sht3x_humidity"
ATTR_SHT3X_TEMPERATURE: Final = "sht3x_temperature"
ATTR_SIGNAL_STRENGTH: Final = "signal"
ATTR_SPS30_P0: Final = "sps30_p0"
ATTR_SPS30_P4: Final = "sps30_p4"
ATTR_UPTIME: Final = "uptime"

ATTR_ENABLED: Final = "enabled"
ATTR_LABEL: Final = "label"
ATTR_UNIT: Final = "unit"

DEFAULT_NAME: Final = "Nettigo Air Monitor"
DEFAULT_UPDATE_INTERVAL: Final = timedelta(minutes=6)
DOMAIN: Final = "nam"
MANUFACTURER: Final = "Nettigo"

SUFFIX_P1: Final = "_p1"
SUFFIX_P2: Final = "_p2"

AIR_QUALITY_SENSORS: Final[dict[str, str]] = {"sds": "SDS011", "sps30": "SPS30"}

SENSORS: Final[dict[str, SensorDescription]] = {
    ATTR_BME280_HUMIDITY: {
        ATTR_LABEL: f"{DEFAULT_NAME} BME280 Humidity",
        ATTR_UNIT: PERCENTAGE,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_HUMIDITY,
        ATTR_ICON: None,
        ATTR_ENABLED: True,
    },
    ATTR_BME280_PRESSURE: {
        ATTR_LABEL: f"{DEFAULT_NAME} BME280 Pressure",
        ATTR_UNIT: PRESSURE_HPA,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_PRESSURE,
        ATTR_ICON: None,
        ATTR_ENABLED: True,
    },
    ATTR_BME280_TEMPERATURE: {
        ATTR_LABEL: f"{DEFAULT_NAME} BME280 Temperature",
        ATTR_UNIT: TEMP_CELSIUS,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_ICON: None,
        ATTR_ENABLED: True,
    },
    ATTR_BMP280_PRESSURE: {
        ATTR_LABEL: f"{DEFAULT_NAME} BMP280 Pressure",
        ATTR_UNIT: PRESSURE_HPA,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_PRESSURE,
        ATTR_ICON: None,
        ATTR_ENABLED: True,
    },
    ATTR_BMP280_TEMPERATURE: {
        ATTR_LABEL: f"{DEFAULT_NAME} BMP280 Temperature",
        ATTR_UNIT: TEMP_CELSIUS,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_ICON: None,
        ATTR_ENABLED: True,
    },
    ATTR_HECA_HUMIDITY: {
        ATTR_LABEL: f"{DEFAULT_NAME} HECA Humidity",
        ATTR_UNIT: PERCENTAGE,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_HUMIDITY,
        ATTR_ICON: None,
        ATTR_ENABLED: True,
    },
    ATTR_HECA_TEMPERATURE: {
        ATTR_LABEL: f"{DEFAULT_NAME} HECA Temperature",
        ATTR_UNIT: TEMP_CELSIUS,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_ICON: None,
        ATTR_ENABLED: True,
    },
    ATTR_SHT3X_HUMIDITY: {
        ATTR_LABEL: f"{DEFAULT_NAME} SHT3X Humidity",
        ATTR_UNIT: PERCENTAGE,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_HUMIDITY,
        ATTR_ICON: None,
        ATTR_ENABLED: True,
    },
    ATTR_SHT3X_TEMPERATURE: {
        ATTR_LABEL: f"{DEFAULT_NAME} SHT3X Temperature",
        ATTR_UNIT: TEMP_CELSIUS,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_ICON: None,
        ATTR_ENABLED: True,
    },
    ATTR_SPS30_P0: {
        ATTR_LABEL: f"{DEFAULT_NAME} SPS30 Particulate Matter 1.0",
        ATTR_UNIT: CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        ATTR_DEVICE_CLASS: None,
        ATTR_ICON: "mdi:blur",
        ATTR_ENABLED: True,
    },
    ATTR_SPS30_P4: {
        ATTR_LABEL: f"{DEFAULT_NAME} SPS30 Particulate Matter 4.0",
        ATTR_UNIT: CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        ATTR_DEVICE_CLASS: None,
        ATTR_ICON: "mdi:blur",
        ATTR_ENABLED: True,
    },
    ATTR_DHT22_HUMIDITY: {
        ATTR_LABEL: f"{DEFAULT_NAME} DHT22 Humidity",
        ATTR_UNIT: PERCENTAGE,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_HUMIDITY,
        ATTR_ICON: None,
        ATTR_ENABLED: True,
    },
    ATTR_DHT22_TEMPERATURE: {
        ATTR_LABEL: f"{DEFAULT_NAME} DHT22 Temperature",
        ATTR_UNIT: TEMP_CELSIUS,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_ICON: None,
        ATTR_ENABLED: True,
    },
    ATTR_SIGNAL_STRENGTH: {
        ATTR_LABEL: f"{DEFAULT_NAME} Signal Strength",
        ATTR_UNIT: SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_SIGNAL_STRENGTH,
        ATTR_ICON: None,
        ATTR_ENABLED: False,
    },
    ATTR_UPTIME: {
        ATTR_LABEL: f"{DEFAULT_NAME} Uptime",
        ATTR_UNIT: None,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TIMESTAMP,
        ATTR_ICON: None,
        ATTR_ENABLED: False,
    },
}
