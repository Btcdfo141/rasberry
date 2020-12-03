"""Test the Qbittorrent Flow."""

from homeassistant import data_entry_flow
from homeassistant.components.qbittorrent.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME

from . import _create_mocked_client

from tests.async_mock import patch


async def test_show_form(hass):
    """Test that the form is served with no input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == SOURCE_USER


async def test_invalid_credentials(hass):
    """Test handle invalid credentials."""
    mocked_client = _create_mocked_client(True)
    with patch(
        "homeassistant.components.qbittorrent.client.Client.login",
        return_value=mocked_client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_URL: "http://testurl.org",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}
