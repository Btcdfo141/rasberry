"""Test the Wallbox config flow."""
import json

import requests_mock

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.wallbox import config_flow
from homeassistant.components.wallbox.const import DOMAIN
from homeassistant.core import HomeAssistant

from tests.components.wallbox import entry, setup_integration

test_response = json.loads(
    '{"charging_power": 0,"max_available_power": "xx","charging_speed": 0,"added_range": "xx","added_energy": "44.697","config_data":{"max_charging_current": "24"}}'
)


async def test_show_set_form(hass: HomeAssistant) -> None:
    """Test that the setup form is served."""
    flow = config_flow.ConfigFlow()
    flow.hass = hass
    result = await flow.async_step_user(user_input=None)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"


async def test_form_cannot_authenticate(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with requests_mock.Mocker() as mock_request:
        mock_request.get(
            "https://api.wall-box.com/auth/token/user",
            text='{"jwt":"fakekeyhere","user_id":12345,"ttl":145656758,"error":false,"status":200}',
            status_code=403,
        )
        mock_request.get(
            "https://api.wall-box.com/chargers/status/12345",
            json=test_response,
            status_code=403,
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "station": "12345",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with requests_mock.Mocker() as mock_request:
        mock_request.get(
            "https://api.wall-box.com/auth/token/user",
            text='{"jwt":"fakekeyhere","user_id":12345,"ttl":145656758,"error":false,"status":200}',
            status_code=404,
        )
        mock_request.get(
            "https://api.wall-box.com/chargers/status/12345",
            json=test_response,
            status_code=404,
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "station": "12345",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_validate_input(hass):
    """Test we can validate input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with requests_mock.Mocker() as mock_request:
        mock_request.get(
            "https://api.wall-box.com/auth/token/user",
            text='{"jwt":"fakekeyhere","user_id":12345,"ttl":145656758,"error":false,"status":200}',
            status_code=200,
        )
        mock_request.get(
            "https://api.wall-box.com/chargers/status/12345",
            json=test_response,
            status_code=200,
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "station": "12345",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["title"] == "Wallbox Portal"
    assert result2["data"]["station"] == "12345"


async def test_form_reauth(hass):
    """Test we handle cannot connect error."""
    await setup_integration(hass)
    assert entry.state == config_entries.ConfigEntryState.LOADED

    with requests_mock.Mocker() as mock_request:
        mock_request.get(
            "https://api.wall-box.com/auth/token/user",
            text='{"jwt":"fakekeyhere","user_id":12345,"ttl":145656758,"error":false,"status":200}',
            status_code=200,
        )
        mock_request.get(
            "https://api.wall-box.com/chargers/status/12345",
            json=test_response,
            status_code=200,
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "station": "12345",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] == "abort"
    assert result2["reason"] == "reauth_successful"

    print(result2)

    await hass.config_entries.async_unload(entry.entry_id)
