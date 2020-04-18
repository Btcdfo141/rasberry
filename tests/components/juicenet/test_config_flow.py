"""Test the JuiceNet config flow."""
from asynctest import patch
from asynctest.mock import MagicMock

from homeassistant import config_entries, setup
from homeassistant.components.juicenet.config_flow import CannotConnect, InvalidAuth
from homeassistant.components.juicenet.const import DOMAIN
from homeassistant.const import CONF_ACCESS_TOKEN


def _mock_juicenet_return_value(get_devices=None):
    juicenet_mock = MagicMock()
    type(juicenet_mock).get_devices = MagicMock(return_value=get_devices)
    return juicenet_mock


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    juicenet_mock = MagicMock()
    type(juicenet_mock).get_devices = MagicMock(return_value=[])

    with patch(
        "homeassistant.components.juicenet.config_flow.Api", return_value=juicenet_mock
    ), patch(
        "homeassistant.components.juicenet.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.juicenet.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ACCESS_TOKEN: "access_token"}
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "JuiceNet"
    assert result2["data"] == {CONF_ACCESS_TOKEN: "access_token"}
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    juicenet_mock = MagicMock()
    type(juicenet_mock).get_devices = MagicMock(side_effect=ValueError)

    with patch(
        "homeassistant.components.juicenet.config_flow.Api", return_value=juicenet_mock
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ACCESS_TOKEN: "access_token"}
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    juicenet_mock = MagicMock()
    type(juicenet_mock).get_devices = MagicMock(side_effect=Exception)

    with patch(
        "homeassistant.components.juicenet.config_flow.Api", return_value=juicenet_mock
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ACCESS_TOKEN: "access_token"}
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}
