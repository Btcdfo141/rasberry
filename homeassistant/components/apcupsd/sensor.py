"""Support for APCUPSd sensors."""
from __future__ import annotations

import copy
import logging

from apcaccess.status import ALL_UNITS
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_RESOURCES,
    ELECTRIC_CURRENT_AMPERE,
    ELECTRIC_POTENTIAL_VOLT,
    FREQUENCY_HERTZ,
    PERCENTAGE,
    POWER_VOLT_AMPERE,
    POWER_WATT,
    TEMP_CELSIUS,
    TIME_MINUTES,
    TIME_SECONDS,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, APCUPSdData

_LOGGER = logging.getLogger(__name__)

SENSORS: dict[str, SensorEntityDescription] = {
    "alarmdel": SensorEntityDescription(
        key="alarmdel",
        name="UPS Alarm Delay",
        icon="mdi:alarm",
    ),
    "ambtemp": SensorEntityDescription(
        key="ambtemp",
        name="UPS Ambient Temperature",
        icon="mdi:thermometer",
    ),
    "apc": SensorEntityDescription(
        key="apc",
        name="UPS Status Data",
        icon="mdi:information-outline",
    ),
    "apcmodel": SensorEntityDescription(
        key="apcmodel",
        name="UPS Model",
        icon="mdi:information-outline",
    ),
    "badbatts": SensorEntityDescription(
        key="badbatts",
        name="UPS Bad Batteries",
        icon="mdi:information-outline",
    ),
    "battdate": SensorEntityDescription(
        key="battdate",
        name="UPS Battery Replaced",
        icon="mdi:calendar-clock",
    ),
    "battstat": SensorEntityDescription(
        key="battstat",
        name="UPS Battery Status",
        icon="mdi:information-outline",
    ),
    "battv": SensorEntityDescription(
        key="battv",
        name="UPS Battery Voltage",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        icon="mdi:flash",
    ),
    "bcharge": SensorEntityDescription(
        key="bcharge",
        name="UPS Battery",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery",
    ),
    "cable": SensorEntityDescription(
        key="cable",
        name="UPS Cable Type",
        icon="mdi:ethernet-cable",
    ),
    "cumonbatt": SensorEntityDescription(
        key="cumonbatt",
        name="UPS Total Time on Battery",
        icon="mdi:timer-outline",
    ),
    "date": SensorEntityDescription(
        key="date",
        name="UPS Status Date",
        icon="mdi:calendar-clock",
    ),
    "dipsw": SensorEntityDescription(
        key="dipsw",
        name="UPS Dip Switch Settings",
        icon="mdi:information-outline",
    ),
    "dlowbatt": SensorEntityDescription(
        key="dlowbatt",
        name="UPS Low Battery Signal",
        icon="mdi:clock-alert",
    ),
    "driver": SensorEntityDescription(
        key="driver",
        name="UPS Driver",
        icon="mdi:information-outline",
    ),
    "dshutd": SensorEntityDescription(
        key="dshutd",
        name="UPS Shutdown Delay",
        icon="mdi:timer-outline",
    ),
    "dwake": SensorEntityDescription(
        key="dwake",
        name="UPS Wake Delay",
        icon="mdi:timer-outline",
    ),
    "end apc": SensorEntityDescription(
        key="end apc",
        name="UPS Date and Time",
        icon="mdi:calendar-clock",
    ),
    "extbatts": SensorEntityDescription(
        key="extbatts",
        name="UPS External Batteries",
        icon="mdi:information-outline",
    ),
    "firmware": SensorEntityDescription(
        key="firmware",
        name="UPS Firmware Version",
        icon="mdi:information-outline",
    ),
    "hitrans": SensorEntityDescription(
        key="hitrans",
        name="UPS Transfer High",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        icon="mdi:flash",
    ),
    "hostname": SensorEntityDescription(
        key="hostname",
        name="UPS Hostname",
        icon="mdi:information-outline",
    ),
    "humidity": SensorEntityDescription(
        key="humidity",
        name="UPS Ambient Humidity",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:water-percent",
    ),
    "itemp": SensorEntityDescription(
        key="itemp",
        name="UPS Internal Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "lastxfer": SensorEntityDescription(
        key="lastxfer",
        name="UPS Last Transfer",
        icon="mdi:transfer",
    ),
    "linefail": SensorEntityDescription(
        key="linefail",
        name="UPS Input Voltage Status",
        icon="mdi:information-outline",
    ),
    "linefreq": SensorEntityDescription(
        key="linefreq",
        name="UPS Line Frequency",
        native_unit_of_measurement=FREQUENCY_HERTZ,
        icon="mdi:information-outline",
    ),
    "linev": SensorEntityDescription(
        key="linev",
        name="UPS Input Voltage",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        icon="mdi:flash",
    ),
    "loadpct": SensorEntityDescription(
        key="loadpct",
        name="UPS Load",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:gauge",
    ),
    "loadapnt": SensorEntityDescription(
        key="loadapnt",
        name="UPS Load Apparent Power",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:gauge",
    ),
    "lotrans": SensorEntityDescription(
        key="lotrans",
        name="UPS Transfer Low",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        icon="mdi:flash",
    ),
    "mandate": SensorEntityDescription(
        key="mandate",
        name="UPS Manufacture Date",
        icon="mdi:calendar",
    ),
    "masterupd": SensorEntityDescription(
        key="masterupd",
        name="UPS Master Update",
        icon="mdi:information-outline",
    ),
    "maxlinev": SensorEntityDescription(
        key="maxlinev",
        name="UPS Input Voltage High",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        icon="mdi:flash",
    ),
    "maxtime": SensorEntityDescription(
        key="maxtime",
        name="UPS Battery Timeout",
        icon="mdi:timer-off-outline",
    ),
    "mbattchg": SensorEntityDescription(
        key="mbattchg",
        name="UPS Battery Shutdown",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery-alert",
    ),
    "minlinev": SensorEntityDescription(
        key="minlinev",
        name="UPS Input Voltage Low",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        icon="mdi:flash",
    ),
    "mintimel": SensorEntityDescription(
        key="mintimel",
        name="UPS Shutdown Time",
        icon="mdi:timer-outline",
    ),
    "model": SensorEntityDescription(
        key="model",
        name="UPS Model",
        icon="mdi:information-outline",
    ),
    "nombattv": SensorEntityDescription(
        key="nombattv",
        name="UPS Battery Nominal Voltage",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        icon="mdi:flash",
    ),
    "nominv": SensorEntityDescription(
        key="nominv",
        name="UPS Nominal Input Voltage",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        icon="mdi:flash",
    ),
    "nomoutv": SensorEntityDescription(
        key="nomoutv",
        name="UPS Nominal Output Voltage",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        icon="mdi:flash",
    ),
    "nompower": SensorEntityDescription(
        key="nompower",
        name="UPS Nominal Output Power",
        native_unit_of_measurement=POWER_WATT,
        icon="mdi:flash",
    ),
    "nomapnt": SensorEntityDescription(
        key="nomapnt",
        name="UPS Nominal Apparent Power",
        native_unit_of_measurement=POWER_VOLT_AMPERE,
        icon="mdi:flash",
    ),
    "numxfers": SensorEntityDescription(
        key="numxfers",
        name="UPS Transfer Count",
        icon="mdi:counter",
    ),
    "outcurnt": SensorEntityDescription(
        key="outcurnt",
        name="UPS Output Current",
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
        icon="mdi:flash",
    ),
    "outputv": SensorEntityDescription(
        key="outputv",
        name="UPS Output Voltage",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
        icon="mdi:flash",
    ),
    "reg1": SensorEntityDescription(
        key="reg1",
        name="UPS Register 1 Fault",
        icon="mdi:information-outline",
    ),
    "reg2": SensorEntityDescription(
        key="reg2",
        name="UPS Register 2 Fault",
        icon="mdi:information-outline",
    ),
    "reg3": SensorEntityDescription(
        key="reg3",
        name="UPS Register 3 Fault",
        icon="mdi:information-outline",
    ),
    "retpct": SensorEntityDescription(
        key="retpct",
        name="UPS Restore Requirement",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery-alert",
    ),
    "selftest": SensorEntityDescription(
        key="selftest",
        name="UPS Last Self Test",
        icon="mdi:calendar-clock",
    ),
    "sense": SensorEntityDescription(
        key="sense",
        name="UPS Sensitivity",
        icon="mdi:information-outline",
    ),
    "serialno": SensorEntityDescription(
        key="serialno",
        name="UPS Serial Number",
        icon="mdi:information-outline",
    ),
    "starttime": SensorEntityDescription(
        key="starttime",
        name="UPS Startup Time",
        icon="mdi:calendar-clock",
    ),
    "statflag": SensorEntityDescription(
        key="statflag",
        name="UPS Status Flag",
        icon="mdi:information-outline",
    ),
    "status": SensorEntityDescription(
        key="status",
        name="UPS Status",
        icon="mdi:information-outline",
    ),
    "stesti": SensorEntityDescription(
        key="stesti",
        name="UPS Self Test Interval",
        icon="mdi:information-outline",
    ),
    "timeleft": SensorEntityDescription(
        key="timeleft",
        name="UPS Time Left",
        icon="mdi:clock-alert",
    ),
    "tonbatt": SensorEntityDescription(
        key="tonbatt",
        name="UPS Time on Battery",
        icon="mdi:timer-outline",
    ),
    "upsmode": SensorEntityDescription(
        key="upsmode",
        name="UPS Mode",
        icon="mdi:information-outline",
    ),
    "upsname": SensorEntityDescription(
        key="upsname",
        name="UPS Name",
        icon="mdi:information-outline",
    ),
    "version": SensorEntityDescription(
        key="version",
        name="UPS Daemon Info",
        icon="mdi:information-outline",
    ),
    "xoffbat": SensorEntityDescription(
        key="xoffbat",
        name="UPS Transfer from Battery",
        icon="mdi:transfer",
    ),
    "xoffbatt": SensorEntityDescription(
        key="xoffbatt",
        name="UPS Transfer from Battery",
        icon="mdi:transfer",
    ),
    "xonbatt": SensorEntityDescription(
        key="xonbatt",
        name="UPS Transfer to Battery",
        icon="mdi:transfer",
    ),
}

SPECIFIC_UNITS = {"ITEMP": TEMP_CELSIUS}
INFERRED_UNITS = {
    " Minutes": TIME_MINUTES,
    " Seconds": TIME_SECONDS,
    " Percent": PERCENTAGE,
    " Volts": ELECTRIC_POTENTIAL_VOLT,
    " Ampere": ELECTRIC_CURRENT_AMPERE,
    " Volt-Ampere": POWER_VOLT_AMPERE,
    " Watts": POWER_WATT,
    " Hz": FREQUENCY_HERTZ,
    " C": TEMP_CELSIUS,
    " Percent Load Capacity": PERCENTAGE,
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_RESOURCES, default=[]): vol.All(
            cv.ensure_list, [vol.In([desc.key for desc in SENSORS.values()])]
        )
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Import the configurations from YAML to config flows."""
    # This is the second step of YAML config imports, first see the comments in
    # async_setup() of __init__.py to get an idea of how we import the YAML configs.

    # Here we retrieve the partial YAML configs from the special entry id, if it does
    # not exist it means it has already been imported.
    conf = hass.data[DOMAIN].get(SOURCE_IMPORT)
    if conf is None:
        return

    _LOGGER.warning(
        "Configuration of apcupsd in YAML is deprecated and will be "
        "removed in Home Assistant 2022.12; Your existing configuration "
        "has been imported into the UI automatically and can be safely removed "
        "from your configuration.yaml file"
    )

    # Remove the artificial entry since it's no longer needed.
    hass.data[DOMAIN].pop(SOURCE_IMPORT)

    # Our config flow allows an extra field CONF_RESOURCES and will import properly as
    # options (although not shown in UI during config setup).
    conf[CONF_RESOURCES] = [res.upper() for res in config[CONF_RESOURCES]]

    _LOGGER.warning(
        "YAML configurations loaded with host %s, port %s and resources %s ",
        conf[CONF_HOST],
        conf[CONF_PORT],
        conf[CONF_RESOURCES],
    )

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
        )
    )

    return


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the APCUPSd sensors from config entries."""
    data_service = hass.data[DOMAIN][config_entry.entry_id]

    available_resources: set[str] = set(data_service.status)

    # We use user-specified resources from imported YAML config (if available).
    specified_resources = available_resources
    if CONF_RESOURCES in config_entry.data:
        resources = config_entry.data.get(CONF_RESOURCES)
        assert isinstance(resources, list)
        specified_resources = set(resources)

    entities = []
    for resource in specified_resources:
        # The resource from data service are in upper-case by default, but we use
        # lower cases inside this integration.
        resource = resource.lower()
        if resource not in SENSORS:
            _LOGGER.warning("Invalid resource from APCUPSd: %s", resource)
            continue
        if resource not in available_resources:
            _LOGGER.warning("Resource %s not available", resource)
            continue

        description = copy.copy(SENSORS[resource])
        # To avoid breaking changes, we disable sensors not specified in resources.
        description.entity_registry_enabled_default = resource in specified_resources
        entities.append(APCUPSdSensor(data_service, description))

    async_add_entities(entities, update_before_add=True)


def infer_unit(value):
    """If the value ends with any of the units from ALL_UNITS.

    Split the unit off the end of the value and return the value, unit tuple
    pair. Else return the original value and None as the unit.
    """

    for unit in ALL_UNITS:
        if value.endswith(unit):
            return value[: -len(unit)], INFERRED_UNITS.get(unit, unit.strip())
    return value, None


class APCUPSdSensor(SensorEntity):
    """Representation of a sensor entity for APCUPSd status values."""

    def __init__(
        self, data_service: APCUPSdData, description: SensorEntityDescription
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._data_service = data_service

    def update(self) -> None:
        """Get the latest status and use it to update our sensor state."""
        self._data_service.update()

        key = self.entity_description.key.upper()
        if key not in self._data_service.status:
            self._attr_native_value = None
            return

        self._attr_native_value, inferred_unit = infer_unit(
            self._data_service.status[key]
        )
        if not self.native_unit_of_measurement:
            self._attr_native_unit_of_measurement = inferred_unit
