"""Unit system helper class and methods."""

import logging
from numbers import Number
from homeassistant.const import (
    TEMP_CELSIUS, TEMP_FAHRENHEIT, LENGTH_CENTIMETERS, LENGTH_METERS,
    LENGTH_KILOMETERS, LENGTH_INCHES, LENGTH_FEET, LENGTH_YARD, LENGTH_MILES,
    VOLUME_LITERS, VOLUME_MILLILITERS, VOLUME_GALLONS, VOLUME_FLUID_OUNCE,
    MASS_GRAMS, MASS_KILOGRAMS, MASS_OUNCES, MASS_POUNDS, CONF_UNIT_SYSTEM_METRIC,
    CONF_UNIT_SYSTEM_IMPERIAL)
from homeassistant.util import temperature as temperature_util
from homeassistant.util import distance as distance_util

_LOGGER = logging.getLogger(__name__)

LENGTH_UNITS = [
    LENGTH_MILES,
    LENGTH_YARD,
    LENGTH_FEET,
    LENGTH_INCHES,
    LENGTH_KILOMETERS,
    LENGTH_METERS,
    LENGTH_CENTIMETERS,
]

MASS_UNITS = [
    MASS_POUNDS,
    MASS_OUNCES,
    MASS_KILOGRAMS,
    MASS_GRAMS,
]

VOLUME_UNITS = [
    VOLUME_GALLONS,
    VOLUME_FLUID_OUNCE,
    VOLUME_LITERS,
    VOLUME_MILLILITERS,
]

TEMPERATURE_UNITS = [
    TEMP_FAHRENHEIT,
    TEMP_CELSIUS,
]


def is_valid_unit(unit: str, unit_type: str) -> bool:
    """Check if the unit is valid for it's type."""
    if unit_type == TYPE_LENGTH:
        units = LENGTH_UNITS
    elif unit_type == TYPE_TEMPERATURE:
        units = TEMPERATURE_UNITS
    elif unit_type == TYPE_MASS:
        units = MASS_UNITS
    elif unit_type == TYPE_VOLUME:
        units = VOLUME_UNITS
    else:
        return False

    return unit in units


class UnitSystem(object):
    """A container for units of measure."""

    # pylint: disable=too-many-arguments
    def __init__(self: object, name: str, temperature: str, length: str,
                 volume: str, mass: str) -> None:
        """Initialize the unit system object."""
        errors = \
            ', '.join(NOT_RECOGNIZED_TEMPLATE.format(unit, unit_type)
                      for unit, unit_type in [
                          (temperature, TYPE_TEMPERATURE),
                          (length, TYPE_LENGTH),
                          (volume, TYPE_VOLUME),
                          (mass, TYPE_MASS), ]
                      if not is_valid_unit(unit, unit_type))  # type: str

        if errors:
            raise ValueError(errors)

        self.name = name
        self.temperature_unit = temperature
        self.length_unit = length
        self.mass_unit = mass
        self.volume_unit = volume

    @property
    def is_metric(self: object) -> bool:
        return self.name == CONF_UNIT_SYSTEM_METRIC

    def temperature(self: object, temperature: float, from_unit: str) -> (
            float, str):
        """Convert the given temperature to this unit system."""
        if not isinstance(temperature, Number):
            return temperature, from_unit

        return temperature_util.convert(temperature,
                                        from_unit, self.temperature_unit)

    def length(self: object, length: float, from_unit: str) -> float:
        """Convert the given length to this unit system."""
        if not isinstance(length, Number):
            return length, from_unit

        return distance_util.convert(length, from_unit,
                                     self.length_unit)  # type: float

    def as_dict(self) -> dict:
        """Convert the unit system to a dictionary."""
        return {
            TYPE_LENGTH: self.length_unit,
            TYPE_MASS: self.mass_unit,
            TYPE_TEMPERATURE: self.temperature_unit,
            TYPE_VOLUME: self.volume_unit
        }


METRIC_SYSTEM = UnitSystem(CONF_UNIT_SYSTEM_METRIC, TEMP_CELSIUS, LENGTH_KILOMETERS,
                           VOLUME_LITERS, MASS_GRAMS)

IMPERIAL_SYSTEM = UnitSystem(CONF_UNIT_SYSTEM_IMPERIAL, TEMP_FAHRENHEIT, LENGTH_MILES,
                             VOLUME_GALLONS, MASS_POUNDS)
