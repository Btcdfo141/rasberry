"""Test config flow for Twitch."""
from unittest.mock import patch

from homeassistant.components.twitch.const import CONF_CHANNELS, DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_entry_oauth2_flow

from tests.components.twitch import TwitchMock
from tests.components.twitch.conftest import CLIENT_ID, SCOPES, TWITCH_AUTHORIZE_URI
from tests.typing import ClientSessionGenerator


async def test_full_flow(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    current_request_with_host: None,
) -> None:
    """Check full flow."""
    result = await hass.config_entries.flow.async_init(
        "twitch", context={"source": SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        hass,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )

    assert result["url"] == (
        f"{TWITCH_AUTHORIZE_URI}?response_type=code&client_id={CLIENT_ID}"
        "&redirect_uri=https://example.com/auth/external/callback"
        f"&state={state}&scope={'+'.join(SCOPES)}"
    )

    client = await hass_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    with patch(
        "homeassistant.components.twitch.async_setup_entry", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.twitch.sensor.Twitch", return_value=TwitchMock()
    ), patch(
        "homeassistant.components.twitch.config_flow.Twitch", return_value=TwitchMock()
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"])

        assert len(hass.config_entries.async_entries(DOMAIN)) == 1
        assert len(mock_setup.mock_calls) == 1

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "channel123"
        assert "result" in result
        assert "token" in result["result"].data
        assert result["result"].data["token"]["access_token"] == "mock-access-token"
        assert result["result"].data["token"]["refresh_token"] == "mock-refresh-token"
        assert result["options"] == {CONF_CHANNELS: ["internetofthings"]}
