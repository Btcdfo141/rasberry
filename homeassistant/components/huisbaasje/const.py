"""Constants for the Huisbaasje integration."""
from homeassistant.const import VOLUME_CUBIC_METERS, TIME_HOURS
from huisbaasje.const import (
    SOURCE_TYPE_ELECTRICITY,
    SOURCE_TYPE_ELECTRICITY_IN,
    SOURCE_TYPE_ELECTRICITY_IN_LOW,
    SOURCE_TYPE_ELECTRICITY_OUT,
    SOURCE_TYPE_ELECTRICITY_OUT_LOW,
    SOURCE_TYPE_ELECTRICITY_EXPECTED,
    SOURCE_TYPE_ELECTRICITY_GOAL,
    SOURCE_TYPE_GAS,
    SOURCE_TYPE_GAS_EXPECTED,
    SOURCE_TYPE_GAS_GOAL,
)

DOMAIN = "huisbaasje"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"

FLOW_CUBIC_METERS_PER_HOUR = f"{VOLUME_CUBIC_METERS}/{TIME_HOURS}"

SOURCE_TYPES = [
    SOURCE_TYPE_ELECTRICITY,
    SOURCE_TYPE_ELECTRICITY_IN,
    SOURCE_TYPE_ELECTRICITY_IN_LOW,
    SOURCE_TYPE_ELECTRICITY_OUT,
    SOURCE_TYPE_ELECTRICITY_OUT_LOW,
    SOURCE_TYPE_GAS,
]

SENSOR_TYPE_RATE = "rate"
SENSOR_TYPE_THIS_DAY = "thisDay"


POLLING_INTERVAL = 10
"""Interval in seconds between polls to huisbaasje"""
