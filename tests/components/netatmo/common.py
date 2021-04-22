"""Common methods used across tests for Netatmo."""
from contextlib import contextmanager
import json
from unittest.mock import patch

from homeassistant.components.webhook import async_handle_webhook
from homeassistant.util.aiohttp import MockRequest

from tests.common import load_fixture

CLIENT_ID = "1234"
CLIENT_SECRET = "5678"
ALL_SCOPES = [
    "read_station",
    "read_camera",
    "access_camera",
    "write_camera",
    "read_presence",
    "access_presence",
    "write_presence",
    "read_homecoach",
    "read_smokedetector",
    "read_thermostat",
    "write_thermostat",
]

COMMON_RESPONSE = {
    "user_id": "91763b24c43d3e344f424e8d",
    "home_id": "91763b24c43d3e344f424e8b",
    "home_name": "MYHOME",
    "user": {"id": "91763b24c43d3e344f424e8b", "email": "john@doe.com"},
}

TEST_TIME = 1559347200.0

FAKE_WEBHOOK_ACTIVATION = {
    "push_type": "webhook_activation",
}

DEFAULT_PLATFORMS = ["camera", "climate", "light", "sensor"]


async def fake_post_request(**args):
    """Return fake data."""
    if "url" not in args:
        return "{}"

    endpoint = args["url"].split("/")[-1]

    if endpoint in "snapshot_720.jpg":
        return b"test stream image bytes"

    if endpoint in [
        "setpersonsaway",
        "setpersonshome",
        "setstate",
        "setroomthermpoint",
        "setthermmode",
        "switchhomeschedule",
    ]:
        return f'{{"{endpoint}": true}}'

    return json.loads(load_fixture(f"netatmo/{endpoint}.json"))


async def fake_post_request_no_data(**args):
    """Fake error during requesting backend data."""
    return "{}"


async def simulate_webhook(hass, webhook_id, response):
    """Simulate a webhook event."""
    request = MockRequest(
        content=bytes(json.dumps({**COMMON_RESPONSE, **response}), "utf-8"),
        mock_source="test",
    )
    await async_handle_webhook(hass, webhook_id, request)
    await hass.async_block_till_done()


@contextmanager
def selected_platforms(platforms):
    """Restrict loaded platforms to list given."""
    with patch("homeassistant.components.netatmo.PLATFORMS", platforms), patch(
        "homeassistant.components.netatmo.api.AsyncConfigEntryNetatmoAuth"
    ) as mock_auth, patch(
        "homeassistant.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
    ), patch(
        "homeassistant.components.webhook.async_generate_url"
    ):
        mock_auth.return_value.async_post_request.side_effect = fake_post_request
        yield
