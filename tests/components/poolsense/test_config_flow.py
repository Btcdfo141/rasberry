"""Test the PoolSense config flow."""
from asynctest import patch

from homeassistant import data_entry_flow
from homeassistant.components.poolsense.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN


async def test_show_form(hass):
    """Test that the form is served with no input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == SOURCE_USER


async def test_invalid_credentials(hass):
    """Test we handle invalid credentials."""
    with patch(
        "poolsense.PoolSense.test_poolsense_credentials",
        side_effect=invalid_credentials,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_EMAIL: "test-email",
                CONF_PASSWORD: "test-password",
                CONF_TOKEN: "",
            },
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "auth"}


async def test_valid_credentials(hass):
    """Test we handle invalid credentials."""
    with patch(
        "poolsense.PoolSense.test_poolsense_credentials", side_effect=valid_credentials,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_EMAIL: "test-email",
                CONF_PASSWORD: "test-password",
                CONF_TOKEN: "",
            },
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "test-email"


def invalid_credentials(*args):
    """Test we handle invalid credentials."""
    return False


def valid_credentials(*args):
    """Test we handle valid credentials."""
    return True
