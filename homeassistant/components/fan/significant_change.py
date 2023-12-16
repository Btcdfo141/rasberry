"""Helper to test significant Fan state changes."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.significant_change import check_absolute_change

from . import ATTR_PERCENTAGE, ATTR_PERCENTAGE_STEP

INSIGNIFICANT_ATTRIBUTES: set[str] = {ATTR_PERCENTAGE_STEP}


def _check_valid_float(value: str | int | float) -> bool:
    """Check if given value is a valid float."""
    try:
        float(value)
    except ValueError:
        return False
    return True


@callback
def async_check_significant_change(
    hass: HomeAssistant,
    old_state: str,
    old_attrs: dict,
    new_state: str,
    new_attrs: dict,
    **kwargs: Any,
) -> bool | None:
    """Test if state significantly changed."""
    if old_state != new_state:
        return True

    old_attrs_s = set(old_attrs.items())
    new_attrs_s = set(new_attrs.items())
    changed_attrs: set[str] = {item[0] for item in old_attrs_s ^ new_attrs_s}

    for attr_name in changed_attrs:
        if attr_name in INSIGNIFICANT_ATTRIBUTES:
            continue

        if attr_name != ATTR_PERCENTAGE:
            return True

        old_attr_value = old_attrs.get(attr_name)
        new_attr_value = new_attrs.get(attr_name)
        if new_attr_value is None or not _check_valid_float(new_attr_value):
            # New attribute value is invalid, ignore it
            continue

        if old_attr_value is None or not _check_valid_float(old_attr_value):
            # Old attribute value was invalid, we should report again
            return True

        if check_absolute_change(old_attr_value, new_attr_value, 1.0):
            return True

    # no significant attribute change detected
    return False
