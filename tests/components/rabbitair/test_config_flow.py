"""Test the RabbitAir config flow."""
from __future__ import annotations

import asyncio
from typing import Generator
from unittest.mock import Mock, patch

import pytest
from rabbitair import Mode, Model, Speed

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.rabbitair.const import DEFAULT_SCAN_INTERVAL, DOMAIN
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM
from homeassistant.helpers.device_registry import format_mac

from tests.common import MockConfigEntry

TEST_HOST = "1.1.1.1"
TEST_TOKEN = "0123456789abcdef0123456789abcdef"
TEST_MAC = "01:23:45:67:89:AB"
TEST_FIRMWARE = "2.3.17"
TEST_HARDWARE = "1.0.0.4"
TEST_UNIQUE_ID = format_mac(TEST_MAC)
TEST_TITLE = f"RabbitAir-{TEST_MAC.replace(':', '')}"


@pytest.fixture(autouse=True)
def use_mocked_zeroconf(mock_async_zeroconf):
    """Mock zeroconf in all tests."""


@pytest.fixture
def rabbitair_connect() -> Generator[None, None, None]:
    """Mock connection."""
    with patch("rabbitair.UdpClient.get_info", return_value=get_mock_info()), patch(
        "rabbitair.UdpClient.get_state", return_value=get_mock_state()
    ):
        yield


def get_mock_info(mac: str = TEST_MAC) -> Mock:
    """Return a mock device info instance."""
    mock_info = Mock()
    mock_info.mac = mac
    return mock_info


def get_mock_state(
    model: Model | None = Model.A3,
    main_firmware: str | None = TEST_HARDWARE,
    power: bool | None = True,
    mode: Mode | None = Mode.Auto,
    speed: Speed | None = Speed.Low,
    wifi_firmware: str | None = TEST_FIRMWARE,
) -> Mock:
    """Return a mock device state instance."""
    mock_state = Mock()
    mock_state.model = model
    mock_state.main_firmware = main_firmware
    mock_state.power = power
    mock_state.mode = mode
    mock_state.speed = speed
    mock_state.wifi_firmware = wifi_firmware
    return mock_state


@pytest.mark.usefixtures("rabbitair_connect")
async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.rabbitair.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": TEST_HOST,
                "access_token": TEST_TOKEN,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == TEST_TITLE
    assert result2["data"] == {
        "host": TEST_HOST,
        "access_token": TEST_TOKEN,
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    "error_type,base_value",
    [
        (ValueError, "invalid_access_token"),
        (OSError, "invalid_host"),
        (asyncio.TimeoutError, "timeout_connect"),
        (Exception, "cannot_connect"),
    ],
)
async def test_form_cannot_connect(
    hass: HomeAssistant, error_type: type[Exception], base_value: str
) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "rabbitair.UdpClient.get_info",
        side_effect=error_type,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": TEST_HOST,
                "access_token": TEST_TOKEN,
            },
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": base_value}


async def test_form_unknown_error(hass: HomeAssistant) -> None:
    """Test we handle unknown error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.rabbitair.config_flow.validate_input",
        side_effect=Exception,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": TEST_HOST,
                "access_token": TEST_TOKEN,
            },
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "unknown"}


@pytest.mark.usefixtures("rabbitair_connect")
async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow."""
    # Set up config entry.
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_UNIQUE_ID,
        data={
            CONF_HOST: TEST_HOST,
            CONF_ACCESS_TOKEN: TEST_TOKEN,
        },
        title=TEST_TITLE,
        options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
    )
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Options flow with no input results in form.
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    # Options flow with input results in update to entry.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL + 5,
        },
    )

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options == {
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL + 5,
    }
