"""Test the devolo_home_control config flow."""
from unittest.mock import patch

from homeassistant import config_entries, setup
from homeassistant.components.devolo_home_control.const import DOMAIN

from tests.common import mock_coro


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.devolo_home_control.async_setup",
        return_value=mock_coro(True),
    ) as mock_setup, patch(
        "homeassistant.components.devolo_home_control.async_setup_entry",
        return_value=mock_coro(True),
    ) as mock_setup_entry, patch(
        "homeassistant.components.devolo_home_control.config_flow.Mydevolo.credentials_valid",
        return_value=True,
    ), patch(
        "homeassistant.components.devolo_home_control.config_flow.Mydevolo.get_gateway_ids",
        return_value=["123456"],
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "home_control_url": "https://homecontrol.mydevolo.com",
                "mydevolo_url": "https://www.mydevolo.com",
            },
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "devolo Home Control"
    assert result2["data"] == {
        "username": "test-username",
        "password": "test-password",
        "home_control_url": "https://homecontrol.mydevolo.com",
        "mydevolo_url": "https://www.mydevolo.com",
    }

    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_credentials(hass):
    """Test if we get the error message on invalid credentials."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.devolo_home_control.config_flow.Mydevolo.credentials_valid",
        return_value=False,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "home_control_url": "https://homecontrol.mydevolo.com",
                "mydevolo_url": "https://www.mydevolo.com",
            },
        )

        assert result["errors"] == {"base": "invalid_credentials"}
