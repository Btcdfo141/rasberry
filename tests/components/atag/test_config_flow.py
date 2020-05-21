"""Tests for the Atag config flow."""
from pyatag import AtagException

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.atag import DOMAIN
from homeassistant.const import CONF_DEVICE
from homeassistant.core import HomeAssistant

from tests.async_mock import patch
from tests.components.atag import (
    COMPLETE_ENTRY,
    PAIR_REPLY,
    RECEIVE_REPLY,
    USER_INPUT,
    init_integration,
)
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_show_form(hass):
    """Test that the form is served with no input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"


async def test_one_config_allowed(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that only one Atag configuration is allowed."""
    await init_integration(hass, aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"


async def test_connection_error(hass):
    """Test we show user form on Atag connection error."""
    with patch(
        "pyatag.AtagOne.authorize", side_effect=AtagException(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=USER_INPUT,
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "connection_error"}


async def test_full_flow_implementation(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test registering an integration and finishing flow works."""
    aioclient_mock.get(
        "http://127.0.0.1:10000/retrieve", json=RECEIVE_REPLY,
    )
    aioclient_mock.post(
        "http://127.0.0.1:10000/pair", json=PAIR_REPLY,
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=USER_INPUT,
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == COMPLETE_ENTRY[CONF_DEVICE]
    assert result["data"] == COMPLETE_ENTRY
