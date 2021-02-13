"""Tests for the Subaru component config flow."""
# pylint: disable=redefined-outer-name
from copy import deepcopy
from unittest import mock
from unittest.mock import patch

import pytest

from homeassistant import config_entries
from homeassistant.components.subaru import config_flow
from homeassistant.components.subaru.const import (
    CONF_HARD_POLL_INTERVAL,
    DEFAULT_HARD_POLL_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_HARD_POLL_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_PIN, CONF_SCAN_INTERVAL
from subarulink.exceptions import InvalidCredentials, InvalidPIN, SubaruException

from .conftest import TEST_CONFIG, TEST_CREDS, TEST_DEVICE_ID, TEST_PIN, TEST_USERNAME

from tests.common import MockConfigEntry


async def test_user_form_init(user_form):
    """Test the initial user form for first step of the config flow."""
    expected = {
        "data_schema": mock.ANY,
        "description_placeholders": None,
        "errors": None,
        "flow_id": mock.ANY,
        "handler": DOMAIN,
        "step_id": "user",
        "type": "form",
    }
    assert expected == user_form


async def test_user_form_repeat_identifier(hass, user_form):
    """Test we handle repeat identifiers."""
    entry = MockConfigEntry(
        domain=DOMAIN, title=TEST_USERNAME, data=TEST_CREDS, options=None
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.connect",
        return_value=True,
    ) as mock_connect:
        result = await hass.config_entries.flow.async_configure(
            user_form["flow_id"],
            TEST_CREDS,
        )
    assert len(mock_connect.mock_calls) == 0
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


async def test_user_form_cannot_connect(hass, user_form):
    """Test we handle cannot connect error."""
    with patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.connect",
        side_effect=SubaruException(None),
    ) as mock_connect:
        result = await hass.config_entries.flow.async_configure(
            user_form["flow_id"],
            TEST_CREDS,
        )
    assert len(mock_connect.mock_calls) == 1
    assert result["type"] == "abort"
    assert result["reason"] == "cannot_connect"


async def test_user_form_invalid_auth(hass, user_form):
    """Test we handle invalid auth."""
    with patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.connect",
        side_effect=InvalidCredentials("invalidAccount"),
    ) as mock_connect:
        result = await hass.config_entries.flow.async_configure(
            user_form["flow_id"],
            TEST_CREDS,
        )
    assert len(mock_connect.mock_calls) == 1
    assert result["type"] == "form"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_form_pin_not_required(hass, user_form):
    """Test successful login when no PIN is required."""
    with patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.connect",
        return_value=True,
    ) as mock_connect, patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.is_pin_required",
        return_value=False,
    ) as mock_is_pin_required:
        result = await hass.config_entries.flow.async_configure(
            user_form["flow_id"],
            TEST_CREDS,
        )
    assert len(mock_connect.mock_calls) == 2
    assert len(mock_is_pin_required.mock_calls) == 1

    expected = {
        "title": TEST_USERNAME,
        "description": None,
        "description_placeholders": None,
        "flow_id": mock.ANY,
        "result": mock.ANY,
        "handler": DOMAIN,
        "type": "create_entry",
        "version": 1,
        "data": deepcopy(TEST_CONFIG),
    }
    expected["data"][CONF_PIN] = None
    result["data"][CONF_DEVICE_ID] = TEST_DEVICE_ID
    assert expected == result


async def test_pin_form_init(pin_form):
    """Test the pin entry form for second step of the config flow."""
    expected = {
        "data_schema": config_flow.PIN_SCHEMA,
        "description_placeholders": None,
        "errors": None,
        "flow_id": mock.ANY,
        "handler": DOMAIN,
        "step_id": "pin",
        "type": "form",
    }
    assert expected == pin_form


async def test_pin_form_bad_pin_format(hass, pin_form):
    """Test we handle invalid pin."""
    with patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.test_pin",
    ) as mock_test_pin, patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.update_saved_pin",
        return_value=True,
    ) as mock_update_saved_pin:
        result = await hass.config_entries.flow.async_configure(
            pin_form["flow_id"], user_input={CONF_PIN: "abcd"}
        )
    assert len(mock_test_pin.mock_calls) == 0
    assert len(mock_update_saved_pin.mock_calls) == 1
    assert result["type"] == "form"
    assert result["errors"] == {"base": "bad_pin_format"}


async def test_pin_form_success(hass, pin_form):
    """Test successful PIN entry."""
    with patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.test_pin",
        return_value=True,
    ) as mock_test_pin, patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.update_saved_pin",
        return_value=True,
    ) as mock_update_saved_pin:
        result = await hass.config_entries.flow.async_configure(
            pin_form["flow_id"], user_input={CONF_PIN: TEST_PIN}
        )

    assert len(mock_test_pin.mock_calls) == 1
    assert len(mock_update_saved_pin.mock_calls) == 1
    expected = {
        "title": TEST_USERNAME,
        "description": None,
        "description_placeholders": None,
        "flow_id": mock.ANY,
        "result": mock.ANY,
        "handler": DOMAIN,
        "type": "create_entry",
        "version": 1,
        "data": TEST_CONFIG,
    }
    result["data"][CONF_DEVICE_ID] = TEST_DEVICE_ID
    assert result == expected


async def test_pin_form_incorrect_pin(hass, pin_form):
    """Test we handle invalid pin."""
    with patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.test_pin",
        side_effect=InvalidPIN("invalidPin"),
    ) as mock_test_pin, patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.update_saved_pin",
        return_value=True,
    ) as mock_update_saved_pin:
        result = await hass.config_entries.flow.async_configure(
            pin_form["flow_id"], user_input={CONF_PIN: TEST_PIN}
        )
    assert len(mock_test_pin.mock_calls) == 1
    assert len(mock_update_saved_pin.mock_calls) == 1
    assert result["type"] == "form"
    assert result["errors"] == {"base": "incorrect_pin"}


async def test_option_flow_form(options_form):
    """Test config flow options form."""
    expected = {
        "data_schema": mock.ANY,
        "description_placeholders": None,
        "errors": None,
        "flow_id": mock.ANY,
        "handler": mock.ANY,
        "step_id": "init",
        "type": "form",
    }
    assert expected == options_form


async def test_option_flow(hass, options_form):
    """Test config flow options."""
    result = await hass.config_entries.options.async_configure(
        options_form["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 350,
            CONF_HARD_POLL_INTERVAL: 3600,
        },
    )
    assert result["type"] == "create_entry"
    assert result["data"] == {
        CONF_SCAN_INTERVAL: 350,
        CONF_HARD_POLL_INTERVAL: 3600,
    }


async def test_option_flow_defaults(hass, options_form):
    """Test config flow options."""
    result = await hass.config_entries.options.async_configure(
        options_form["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_HARD_POLL_INTERVAL: DEFAULT_HARD_POLL_INTERVAL,
        },
    )
    assert result["type"] == "create_entry"
    assert result["data"] == {
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        CONF_HARD_POLL_INTERVAL: DEFAULT_HARD_POLL_INTERVAL,
    }


async def test_option_flow_input_floor(hass, options_form):
    """Test config flow options."""
    result = await hass.config_entries.options.async_configure(
        options_form["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 1,
            CONF_HARD_POLL_INTERVAL: 1,
        },
    )
    assert result["type"] == "create_entry"
    assert result["data"] == {
        CONF_SCAN_INTERVAL: MIN_SCAN_INTERVAL,
        CONF_HARD_POLL_INTERVAL: MIN_HARD_POLL_INTERVAL,
    }


@pytest.fixture
async def user_form(hass):
    """Return initial form for Subaru config flow."""
    return await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


@pytest.fixture
async def pin_form(hass, user_form):
    """Return second form (PIN input) for Subaru config flow."""
    with patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.connect",
        return_value=True,
    ), patch(
        "homeassistant.components.subaru.config_flow.SubaruAPI.is_pin_required",
        return_value=True,
    ):
        return await hass.config_entries.flow.async_configure(
            user_form["flow_id"], user_input=TEST_CREDS
        )


@pytest.fixture
async def options_form(hass):
    """Return options form for Subaru config flow."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=None)
    entry.add_to_hass(hass)
    return await hass.config_entries.options.async_init(entry.entry_id)
