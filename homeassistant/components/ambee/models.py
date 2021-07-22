"""Models helper class for the Ambee integration."""
from __future__ import annotations

from typing import NamedTuple


class AmbeeSensor(NamedTuple):
    """Represent an Ambee Sensor."""

    name: str

    device_class: str | None = None
    enabled_by_default: bool = True
    icon: str | None = None
    state_class: str | None = None
    unit_of_measurement: str | None = None
