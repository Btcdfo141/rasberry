"""Test the Home Assistant Yellow integration helpers."""
from __future__ import annotations

import contextlib
import typing
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components.homeassistant_yellow.helpers import (
    YellowGPIO,
    async_validate_gpio_states,
)
from homeassistant.core import HomeAssistant

if typing.TYPE_CHECKING:
    import gpiod


@contextlib.contextmanager
def mock_gpio_pin_states(pin_states: dict[int, list[bool]]):
    """Mock the GPIO pin read function."""

    read_count = 0

    def mock_request_lines(
        config: dict[int | tuple[int, ...], gpiod.LineSettings], **kwargs
    ):
        all_pins = []

        for pin_or_pins in config:
            if isinstance(pin_or_pins, tuple):
                all_pins.extend(pin_or_pins)
            else:
                all_pins.append(pin_or_pins)

        def mock_get_values() -> list[gpiod.line.Value]:
            nonlocal read_count

            values = [pin_states[pin][read_count] for pin in all_pins]
            read_count += 1

            return values

        mock_request = MagicMock()
        mock_request.get_values.side_effect = mock_get_values

        mock = MagicMock()
        mock.__enter__ = MagicMock(return_value=mock_request)

        return mock

    mock_gpiod = MagicMock()
    mock_gpiod.request_lines = MagicMock(side_effect=mock_request_lines)

    with patch.dict("sys.modules", gpiod=mock_gpiod):
        yield


@pytest.mark.parametrize(
    ("states", "result"),
    [
        (
            # Normal
            {
                YellowGPIO.RADIO_BOOT: [1, 1, 1, 1, 1],
                YellowGPIO.RADIO_RESET: [1, 1, 1, 1, 1],
            },
            True,
        ),
        (
            # Unstable
            {
                YellowGPIO.RADIO_BOOT: [1, 1, 0, 1, 1],
                YellowGPIO.RADIO_RESET: [1, 1, 1, 1, 1],
            },
            False,
        ),
        (
            # Stable but inverted
            {
                YellowGPIO.RADIO_BOOT: [0, 0, 0, 0, 0],
                YellowGPIO.RADIO_RESET: [0, 0, 0, 0, 0],
            },
            False,
        ),
        (
            # Half stable but inverted
            {
                YellowGPIO.RADIO_BOOT: [1, 1, 1, 1, 1],
                YellowGPIO.RADIO_RESET: [0, 0, 0, 0, 0],
            },
            False,
        ),
    ],
)
async def test_validate_gpio_pins(
    states: dict[YellowGPIO, list[int]], result: bool, hass: HomeAssistant
):
    """Test validating GPIO pin states, success."""
    with mock_gpio_pin_states(states):
        assert (await async_validate_gpio_states(hass)) is result
