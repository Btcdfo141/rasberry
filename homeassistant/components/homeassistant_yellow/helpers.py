"""Helper functions for the Yellow."""
from __future__ import annotations

import enum
import time

import gpiod

from homeassistant.core import HomeAssistant


class PinStatesUnstable(Exception):
    """The state of the GPIO pins is unstable."""


class ZigbeeGPIO(enum.IntEnum):
    """Yellow MGM210P GPIO pins."""

    SWDIO = 6  # PCB 30
    SWCLK = 7  # PCB 37
    TXD = 8  # PCB 39
    RXD = 9  # PCB 40
    CTS = 10  # PCB 44
    RTS = 11  # PCB 38
    BOOT = 24  # PCB 45
    RESET = 25  # PCB 41


# Pin states on a properly installed CM4
RUNNING_PIN_STATES = {
    ZigbeeGPIO.BOOT: 1,
    ZigbeeGPIO.RESET: 1,
}


def _read_gpio_pins(pins: list[int]) -> dict[int, bool]:
    """Read the state of the given GPIO pins."""
    chip = gpiod.chip(0, gpiod.chip.OPEN_BY_NUMBER)

    config = gpiod.line_request()
    config.consumer = "core-yellow"
    config.request_type = gpiod.line_request.DIRECTION_INPUT

    values = {}

    for pin in pins:
        line = chip.get_line(pin)

        try:
            line.request(config)
            values[pin] = line.get_value()
        finally:
            line.release()

    return values


def _read_gpio_pins_stable(
    pins: list[int], *, repeat: int = 5, delay: float = 0.01
) -> dict[int, bool]:
    """Read the state of the given GPIO pins and ensure the states are stable."""

    values = _read_gpio_pins(pins)

    for _ in range(repeat - 1):
        time.sleep(delay)
        new_values = _read_gpio_pins(pins)

        if new_values != values:
            raise PinStatesUnstable()

    return values


async def async_validate_gpio_states(hass: HomeAssistant) -> bool:
    """Validate the state of the GPIO pins."""
    try:
        pin_states = await hass.async_add_executor_job(
            _read_gpio_pins_stable, list(RUNNING_PIN_STATES)
        )
    except PinStatesUnstable:
        return False

    return pin_states == RUNNING_PIN_STATES
