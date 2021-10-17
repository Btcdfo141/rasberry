"""Support gathering ted5000 information."""
from contextlib import suppress
from datetime import timedelta
import logging

import requests
import voluptuous as vol
import xmltodict

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
)
from homeassistant.const import (
    ATTR_HIDDEN,
    CONF_HOST,
    CONF_MODE,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CURRENCY_DOLLAR,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_MONETARY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_POWER_FACTOR,
    DEVICE_CLASS_VOLTAGE,
    ELECTRIC_POTENTIAL_VOLT,
    ENERGY_WATT_HOUR,
    PERCENTAGE,
    POWER_WATT,
    TIME_DAYS,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "ted"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=10)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=80): cv.port,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MODE, default="base"): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Ted5000 platform."""
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    name = config.get(CONF_NAME)
    mode = config.get(CONF_MODE)
    interval = config.get(CONF_SCAN_INTERVAL, MIN_TIME_BETWEEN_UPDATES)
    url = f"http://{host}:{port}/api/LiveData.xml"

    lvl = {"base": 1, "advanced": 2, "extended": 3}

    gateway = Ted5000Gateway(url, interval)

    # Get MTU information to create the sensors.
    gateway.update()

    dev = []

    # Create MTU sensors
    for mtu in gateway.data:
        dev.append(Ted5000Sensor(gateway, name, mtu, 0, POWER_WATT))
        dev.append(Ted5000Sensor(gateway, name, mtu, 1, ELECTRIC_POTENTIAL_VOLT))
        if lvl[mode] >= 2:  # advanced or extended
            dev.append(Ted5000Sensor(gateway, name, mtu, 2, ENERGY_WATT_HOUR))
            dev.append(Ted5000Sensor(gateway, name, mtu, 3, ENERGY_WATT_HOUR))
            dev.append(Ted5000Sensor(gateway, name, mtu, 4, PERCENTAGE))

    # Create utility sensors
    if lvl[mode] >= 3:  # extended only
        # MTUs Quantity
        dev.append(Ted5000Utility(gateway, name, 0, ATTR_HIDDEN))
        # Current Rate $/kWh
        dev.append(Ted5000Utility(gateway, name, 1, CURRENCY_DOLLAR))
        # Days left in billing cycle
        dev.append(Ted5000Utility(gateway, name, 2, TIME_DAYS))
        # Plan type (Flat, Tier, TOU, Tier+TOU)
        dev.append(Ted5000Utility(gateway, name, 3, ATTR_HIDDEN))
        # Current Tier (0 = Disabled)
        dev.append(Ted5000Utility(gateway, name, 4, ATTR_HIDDEN))
        # Current TOU (0 = Disabled)
        dev.append(Ted5000Utility(gateway, name, 5, ATTR_HIDDEN))
        # Current TOU Description (if Current TOU is 0 => Not Configured)
        dev.append(Ted5000Utility(gateway, name, 6, ATTR_HIDDEN))
        # Carbon Rate lbs/kW
        dev.append(Ted5000Utility(gateway, name, 7, ATTR_HIDDEN))
        # Meter read date
        dev.append(Ted5000Utility(gateway, name, 8, ATTR_HIDDEN))

    add_entities(dev)
    return True


class Ted5000Sensor(SensorEntity):
    """Implementation of a Ted5000 MTU sensor."""

    def __init__(self, gateway, name, mtu, ptr, unit):
        """Initialize the sensor."""
        dclass = {
            POWER_WATT: DEVICE_CLASS_POWER,
            ELECTRIC_POTENTIAL_VOLT: DEVICE_CLASS_VOLTAGE,
            ENERGY_WATT_HOUR: DEVICE_CLASS_ENERGY,
            PERCENTAGE: DEVICE_CLASS_POWER_FACTOR,
        }
        sclass = {
            POWER_WATT: STATE_CLASS_MEASUREMENT,
            ELECTRIC_POTENTIAL_VOLT: STATE_CLASS_MEASUREMENT,
            ENERGY_WATT_HOUR: STATE_CLASS_TOTAL_INCREASING,
            PERCENTAGE: STATE_CLASS_MEASUREMENT,
        }
        suffix = {
            0: "power",
            1: "voltage",
            2: "energy_daily",
            3: "energy_monthly",
            4: "pf",
        }
        self._gateway = gateway
        self._name = f"{name} mtu{mtu} {suffix[ptr]}"
        self._mtu = mtu
        self._ptr = ptr
        self._unit = unit
        self._dclass = dclass[unit]
        self._sclass = sclass[unit]
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def native_unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit

    @property
    def device_class(self):
        """Return the device class the value is expressed in."""
        return self._dclass

    @property
    def state_class(self):
        """Return the state class the value is expressed in."""
        return self._sclass

    @property
    def native_value(self):
        """Return the state of the resources."""
        with suppress(KeyError):
            return self._gateway.data[self._mtu][self._ptr]

    def update(self):
        """Get the latest data from REST API."""
        self._gateway.update()


class Ted5000Utility(SensorEntity):
    """Implementation of a Ted5000 utility sensors."""

    def __init__(self, gateway, name, ptr, unit):
        """Initialize the sensor."""
        dclass = {
            ATTR_HIDDEN: ATTR_HIDDEN,
            CURRENCY_DOLLAR: DEVICE_CLASS_MONETARY,
            TIME_DAYS: ATTR_HIDDEN,
        }
        sclass = {
            ATTR_HIDDEN: ATTR_HIDDEN,
            CURRENCY_DOLLAR: STATE_CLASS_MEASUREMENT,
            TIME_DAYS: ATTR_HIDDEN,
        }
        units = {
            0: ATTR_HIDDEN,
            1: "$/kWh",
            2: TIME_DAYS,
            3: ATTR_HIDDEN,
            4: ATTR_HIDDEN,
            5: ATTR_HIDDEN,
            6: ATTR_HIDDEN,
            7: "lbs/kW",
            8: ATTR_HIDDEN,
        }
        suffix = {
            0: "MTUs",
            1: "CurrentRate",
            2: "DaysLeftInBillingCycle",
            3: "PlanType",
            4: "CurrentTier",
            5: "CurrentTOU",
            6: "CurrentTOUDescription",
            7: "CarbonRate",
            8: "MeterReadDate",
        }
        self._gateway = gateway
        self._name = f"{name} Utility {suffix[ptr]}"
        self._ptr = ptr
        self._unit = units[ptr]
        self._dclass = dclass[unit]
        self._sclass = sclass[unit]
        self.update()

    @property
    def name(self):
        """Return the friendly_name of the sensor."""
        return self._name

    @property
    def native_unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        if self._unit is not ATTR_HIDDEN:
            return self._unit

    @property
    def device_class(self):
        """Return the device class the value is expressed in."""
        if self._dclass is not ATTR_HIDDEN:
            return self._dclass

    @property
    def state_class(self):
        """Return the state class the value is expressed in."""
        if self._sclass is not ATTR_HIDDEN:
            return self._sclass

    @property
    def native_value(self):
        """Return the state of the resources."""
        with suppress(KeyError):
            return self._gateway.data_utility[self._ptr]

    def update(self):
        """Get the latest data from REST API."""
        self._gateway.update()


class Ted5000Gateway:
    """The class for handling the data retrieval."""

    def __init__(self, url, interval):
        """Initialize the data object."""
        self.url = url
        MIN_TIME_BETWEEN_UPDATES = interval
        self.data = {}
        self.data_utility = {}

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from the Ted5000 XML API."""

        try:
            request = requests.get(self.url, timeout=10)
        except requests.exceptions.RequestException as err:
            _LOGGER.error("No connection to endpoint: %s", err)
        else:
            doc = xmltodict.parse(request.text)
            mtus = int(doc["LiveData"]["System"]["NumberMTU"])

            # MTU data
            for mtu in range(1, mtus + 1):
                power = int(doc["LiveData"]["Power"]["MTU%d" % mtu]["PowerNow"])
                voltage = int(doc["LiveData"]["Voltage"]["MTU%d" % mtu]["VoltageNow"])
                power_factor = int(doc["LiveData"]["Power"]["MTU%d" % mtu]["PF"])
                energy_daily = int(doc["LiveData"]["Power"]["MTU%d" % mtu]["PowerTDY"])
                energy_monthly = int(
                    doc["LiveData"]["Power"]["MTU%d" % mtu]["PowerMTD"]
                )

                self.data[mtu] = {
                    0: power,
                    1: voltage / 10,
                    2: energy_daily,
                    3: energy_monthly,
                    4: power_factor / 10,
                }

            # Utility Data
            current_rate = int(doc["LiveData"]["Utility"]["CurrentRate"])
            days_left = int(
                doc["LiveData"]["Utility"]["DaysLeftInBillingCycle"]
            )
            plan_type = int(doc["LiveData"]["Utility"]["PlanType"])
            plan_type_str = {0: "Flat", 1: "Tier", 2: "TOU", 3: "Tier+TOU"}
            carbon_rate = int(doc["LiveData"]["Utility"]["CarbonRate"])
            read_date = int(doc["LiveData"]["Utility"]["MeterReadDate"])

            if plan_type in (0, 2):
                current_tier = 0
            else:
                current_tier = int(doc["LiveData"]["Utility"]["CurrentTier"]) + 1

            if plan_type < 2:
                current_tou = 0
                current_tou_str = "Not Configured"
            else:
                current_tou = int(doc["LiveData"]["Utility"]["CurrentTOU"]) + 1
                current_tou_str = doc["LiveData"]["Utility"]["CurrentTOUDescription"]

            self.data_utility = {
                0: mtus,
                1: current_rate / 100000,
                2: days_left,
                3: plan_type_str[plan_type],
                4: current_tier,
                5: current_tou,
                6: current_tou_str,
                7: carbon_rate / 100,
                8: read_date,
            }
