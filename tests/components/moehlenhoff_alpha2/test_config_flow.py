"""Test the devolo_home_control config flow."""
from unittest.mock import PropertyMock

from moehlenhoff_alpha2 import Alpha2Base

from homeassistant.components.moehlenhoff_alpha2.const import DOMAIN
from homeassistant.helpers.typing import HomeAssistantType

from tests.async_mock import patch


async def test_duplicate_error(hass: HomeAssistantType):
    """Test that errors are shown when duplicates are added."""
    Alpha2Base.name = PropertyMock(return_value="fake_base_name")
    with patch("moehlenhoff_alpha2.Alpha2Base._fetch_static_data", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data={"host": "fake_host"}
        )
        assert result["title"] == "fake_base_name"
        assert result["type"] == "create_entry"
        assert not result["result"].unique_id

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data={"host": "fake_host"}
        )
        assert result["type"] == "abort"
        assert result["reason"] == "already_configured"


async def test_user(hass: HomeAssistantType):
    """Test starting a flow by user."""

    with patch("moehlenhoff_alpha2.Alpha2Base._fetch_static_data", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"host": "fake_host_user"}
        )
        assert result["type"] == "create_entry"
        assert result["title"] == "fake_base_name"
        assert result["data"]["host"] == "fake_host_user"


async def test_connection_error(hass: HomeAssistantType):
    """Test connection error."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"host": "127.0.0.1"}
    )
    assert result["type"] == "form"
    assert result["errors"]["base"] == "cannot_connect"


async def test_unexpected_error(hass: HomeAssistantType):
    """Test unexpected error."""

    with patch(
        "moehlenhoff_alpha2.Alpha2Base._fetch_static_data",
        side_effect=Exception,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"host": "10.10.10.10"}
        )
        assert result["type"] == "form"
        assert result["errors"]["base"] == "unknown"
