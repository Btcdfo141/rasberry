"""Helper functions for the Yellow."""
from __future__ import annotations

import enum
import time

from homeassistant.core import HomeAssistant

try:
    import gpiod
except ImportError:
    # libgpiod's Python bindings are not available in all OS builds
    gpiod = None


class PinStatesUnstable(Exception):
    """The state of the GPIO pins is unstable."""


class YellowGPIO(enum.IntEnum):
    """Yellow MGM210P GPIO pins."""

    RADIO_SWDIO = 6
    RADIO_SWCLK = 7
    RADIO_TXD = 8
    RADIO_RXD = 9
    RADIO_CTS = 10
    RADIO_RTS = 11
    RADIO_BOOT = 24
    RADIO_RESET = 25
    SW_USER = 26
    SW_WIPE = 27


# Pin states on a properly installed CM4
RUNNING_PIN_STATES = {
    YellowGPIO.RADIO_BOOT: 1,
    YellowGPIO.RADIO_RESET: 1,
}

GPIO_READ_ATTEMPTS = 5
GPIO_READ_DELAY_S = 0.01


def _read_gpio_pins(pins: list[int]) -> dict[int, bool]:
    """Read the state of the given GPIO pins."""
    chip = gpiod.Chip("gpiochip0", gpiod.Chip.OPEN_BY_NAME)
    values = {}

    for pin in pins:
        line = chip.get_line(pin)

        try:
            line.request(consumer="core-yellow", type=gpiod.LINE_REQ_DIR_IN)
            values[pin] = line.get_value()
        finally:
            line.release()

    return values


def _read_gpio_pins_stable(pins: list[int]) -> dict[int, bool]:
    """Read the state of the given GPIO pins and ensure the states are stable."""

    values = _read_gpio_pins(pins)

    for _ in range(GPIO_READ_ATTEMPTS - 1):
        time.sleep(GPIO_READ_DELAY_S)
        new_values = _read_gpio_pins(pins)

        if new_values != values:
            raise PinStatesUnstable()

    return values


async def async_validate_gpio_states(hass: HomeAssistant) -> bool:
    """Validate the state of the GPIO pins."""
    if gpiod is None:
        return True

    try:
        pin_states = await hass.async_add_executor_job(
            _read_gpio_pins_stable, list(RUNNING_PIN_STATES)
        )
    except PinStatesUnstable:
        return False

    return pin_states == RUNNING_PIN_STATES
