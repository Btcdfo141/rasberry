"""Support for Renault services."""
import logging
from types import MappingProxyType

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    REGEX_VIN,
    SERVICE_AC_CANCEL,
    SERVICE_AC_START,
    SERVICE_CHARGE_SET_MODE,
    SERVICE_CHARGE_SET_SCHEDULES,
    SERVICE_CHARGE_START,
    SERVICES,
)
from .renault_hub import RenaultHub
from .renault_vehicle import RenaultVehicleProxy

LOGGER = logging.getLogger(__name__)

SCHEMA_CHARGE_MODE = "charge_mode"
SCHEMA_SCHEDULES = "schedules"
SCHEMA_TEMPERATURE = "temperature"
SCHEMA_VIN = "vin"
SCHEMA_WHEN = "when"

SERVICE_AC_CANCEL_SCHEMA = vol.Schema(
    {
        vol.Required(SCHEMA_VIN): cv.matches_regex(REGEX_VIN),
    }
)
SERVICE_AC_START_SCHEMA = vol.Schema(
    {
        vol.Required(SCHEMA_VIN): cv.matches_regex(REGEX_VIN),
        vol.Required(SCHEMA_TEMPERATURE): cv.positive_float,
        vol.Optional(SCHEMA_WHEN): cv.datetime,
    }
)
SERVICE_CHARGE_SET_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(SCHEMA_VIN): cv.matches_regex(REGEX_VIN),
        vol.Required(SCHEMA_CHARGE_MODE): cv.string,
    }
)
SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA = vol.Schema(
    {
        vol.Required("startTime"): cv.string,
        vol.Required("duration"): cv.positive_int,
    }
)
SERVICE_CHARGE_SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("id"): cv.positive_int,
        vol.Optional("activated"): cv.boolean,
        vol.Optional("monday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
        vol.Optional("tuesday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
        vol.Optional("wednesday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
        vol.Optional("thursday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
        vol.Optional("friday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
        vol.Optional("saturday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
        vol.Optional("sunday"): vol.Schema(SERVICE_CHARGE_SET_SCHEDULE_DAY_SCHEMA),
    }
)
SERVICE_CHARGE_SET_SCHEDULES_SCHEMA = vol.Schema(
    {
        vol.Required(SCHEMA_VIN): cv.matches_regex(REGEX_VIN),
        vol.Required(SCHEMA_SCHEDULES): vol.All(
            cv.ensure_list, [SERVICE_CHARGE_SET_SCHEDULE_SCHEMA]
        ),
    }
)
SERVICE_CHARGE_START_SCHEMA = vol.Schema(
    {
        vol.Required(SCHEMA_VIN): cv.matches_regex(REGEX_VIN),
    }
)


def setup_services(hass: HomeAssistant) -> None:
    """Register the Renault services."""

    async def ac_cancel(service_call: ServiceCall) -> None:
        """Cancel A/C."""
        vehicle = get_vehicle(service_call.data)

        LOGGER.debug("A/C cancel attempt")
        result = await vehicle.send_ac_stop()
        LOGGER.info("A/C cancel result: %s", result)

    async def ac_start(service_call: ServiceCall) -> None:
        """Start A/C."""
        temperature = service_call.data[SCHEMA_TEMPERATURE]
        when = service_call.data.get(SCHEMA_WHEN, None)
        vehicle = get_vehicle(service_call.data)

        LOGGER.debug("A/C start attempt: %s / %s", when, temperature)
        result = await vehicle.send_ac_start(temperature=temperature, when=when)
        LOGGER.info("A/C start result: %s", result.raw_data)

    async def charge_set_mode(service_call: ServiceCall) -> None:
        """Set charge mode."""
        charge_mode: str = service_call.data[SCHEMA_CHARGE_MODE]
        vehicle = get_vehicle(service_call.data)

        LOGGER.debug("Charge set mode attempt: %s", charge_mode)
        result = await vehicle.send_set_charge_mode(charge_mode)
        LOGGER.info("Charge set mode result: %s", result)

    async def charge_set_schedules(service_call: ServiceCall) -> None:
        """Set charge schedules."""
        schedules: list = service_call.data[SCHEMA_SCHEDULES]
        vehicle = get_vehicle(service_call.data)
        charge_schedules = await vehicle.get_charging_settings()
        for schedule in schedules:
            charge_schedules.update(schedule)

        LOGGER.debug("Charge set schedules attempt: %s", schedules)
        result = await vehicle.send_set_charge_schedules(charge_schedules)
        LOGGER.info("Charge set schedules result: %s", result)
        LOGGER.info(
            "It may take some time before these changes are reflected in your vehicle"
        )

    async def charge_start(service_call: ServiceCall) -> None:
        """Start charge."""
        vehicle = get_vehicle(service_call.data)

        LOGGER.debug("Charge start attempt")
        result = await vehicle.send_charge_start()
        LOGGER.info("Charge start result: %s", result)

    def get_vehicle(service_call_data: MappingProxyType) -> RenaultVehicleProxy:
        """Get vehicle from service_call data."""
        vin: str = service_call_data[SCHEMA_VIN]
        proxy: RenaultHub
        for proxy in hass.data[DOMAIN].values():
            vehicle = proxy.vehicles.get(vin)
            if vehicle is not None:
                return vehicle
        raise ValueError(f"Unable to find vehicle with VIN: {vin}")

    hass.services.async_register(
        DOMAIN,
        SERVICE_AC_CANCEL,
        ac_cancel,
        schema=SERVICE_AC_CANCEL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_AC_START,
        ac_start,
        schema=SERVICE_AC_START_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CHARGE_SET_MODE,
        charge_set_mode,
        schema=SERVICE_CHARGE_SET_MODE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CHARGE_SET_SCHEDULES,
        charge_set_schedules,
        schema=SERVICE_CHARGE_SET_SCHEDULES_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CHARGE_START,
        charge_start,
        schema=SERVICE_CHARGE_START_SCHEMA,
    )


def unload_services(hass: HomeAssistant) -> None:
    """Unload Renault services."""
    for service in SERVICES:
        hass.services.async_remove(DOMAIN, service)
