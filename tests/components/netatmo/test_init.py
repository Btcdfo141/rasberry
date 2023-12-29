"""The tests for Netatmo component."""
from contextlib import asynccontextmanager
from datetime import timedelta
from time import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pyatmo
from pyatmo.const import ALL_SCOPES
import pytest

from homeassistant import config_entries
from homeassistant.components.netatmo import DOMAIN
from homeassistant.components.netatmo.const import (
    EXCEPTION_ID_WEBHOOK_HTTPS_REQUIRED,
    EXCEPTION_ID_WEBHOOK_REGISTRATION_FAILED,
    SERVICE_REGISTER_WEBHOOK,
    SERVICE_UNREGISTER_WEBHOOK,
)
from homeassistant.components.webhook import is_registered as is_webhook_registered
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import CoreState, HomeAssistant, HomeAssistantError
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from .common import (
    FAKE_WEBHOOK_ACTIVATION,
    fake_post_request,
    selected_platforms,
    simulate_webhook,
)

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_get_persistent_notifications,
)
from tests.components.cloud import mock_cloud

# Fake webhook thermostat mode change to "Max"
FAKE_WEBHOOK = {
    "room_id": "2746182631",
    "home": {
        "id": "91763b24c43d3e344f424e8b",
        "name": "MYHOME",
        "country": "DE",
        "rooms": [
            {
                "id": "2746182631",
                "name": "Livingroom",
                "type": "livingroom",
                "therm_setpoint_mode": "max",
                "therm_setpoint_end_time": 1612749189,
            }
        ],
        "modules": [
            {"id": "12:34:56:00:01:ae", "name": "Livingroom", "type": "NATherm1"}
        ],
    },
    "mode": "max",
    "event_type": "set_point",
    "push_type": "display_change",
}


@asynccontextmanager
async def setup_for_webhook_tests(hass: HomeAssistant, config_entry):
    """Configure patches and integration for testing webhook management services."""
    with patch(
        "homeassistant.components.netatmo.api.AsyncConfigEntryNetatmoAuth",
    ) as mock_auth, selected_platforms(["camera", "climate", "light", "sensor"]):
        mock_auth.return_value.async_post_api_request.side_effect = fake_post_request
        mock_async_addwebhook: MagicMock = mock_auth.return_value.async_addwebhook
        mock_async_dropwebhook: MagicMock = mock_auth.return_value.async_dropwebhook

        mock_async_addwebhook.side_effect = AsyncMock()
        mock_async_dropwebhook.side_effect = AsyncMock()

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        webhook_id = config_entry.data[CONF_WEBHOOK_ID]
        assert is_webhook_registered(hass, webhook_id)
        mock_async_addwebhook.assert_called_once()
        mock_auth.return_value.async_dropwebhook.assert_not_called()

        mock_async_addwebhook.reset_mock()
        mock_async_dropwebhook.reset_mock()

        yield (mock_async_addwebhook, mock_async_dropwebhook)


async def test_setup_component(hass: HomeAssistant, config_entry) -> None:
    """Test setup and teardown of the netatmo component."""
    with patch(
        "homeassistant.components.netatmo.api.AsyncConfigEntryNetatmoAuth",
    ) as mock_auth, patch(
        "homeassistant.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
    ) as mock_impl, patch(
        "homeassistant.components.netatmo.webhook_generate_url"
    ) as mock_webhook:
        mock_auth.return_value.async_post_api_request.side_effect = fake_post_request
        mock_auth.return_value.async_addwebhook.side_effect = AsyncMock()
        mock_auth.return_value.async_dropwebhook.side_effect = AsyncMock()
        assert await async_setup_component(hass, "netatmo", {})

    await hass.async_block_till_done()

    mock_auth.assert_called_once()
    mock_impl.assert_called_once()
    mock_webhook.assert_called_once()

    assert config_entry.state is config_entries.ConfigEntryState.LOADED
    assert hass.config_entries.async_entries(DOMAIN)
    assert len(hass.states.async_all()) > 0

    for config_entry in hass.config_entries.async_entries("netatmo"):
        await hass.config_entries.async_remove(config_entry.entry_id)

    await hass.async_block_till_done()
    assert len(hass.states.async_all()) == 0
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_setup_component_with_config(hass: HomeAssistant, config_entry) -> None:
    """Test setup of the netatmo component with dev account."""
    fake_post_hits = 0

    async def fake_post(*args, **kwargs):
        """Fake error during requesting backend data."""
        nonlocal fake_post_hits
        fake_post_hits += 1
        return await fake_post_request(*args, **kwargs)

    with patch(
        "homeassistant.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
    ) as mock_impl, patch(
        "homeassistant.components.netatmo.webhook_generate_url"
    ) as mock_webhook, patch(
        "homeassistant.components.netatmo.api.AsyncConfigEntryNetatmoAuth",
    ) as mock_auth, patch(
        "homeassistant.components.netatmo.data_handler.PLATFORMS", ["sensor"]
    ):
        mock_auth.return_value.async_post_api_request.side_effect = fake_post
        mock_auth.return_value.async_addwebhook.side_effect = AsyncMock()
        mock_auth.return_value.async_dropwebhook.side_effect = AsyncMock()

        assert await async_setup_component(
            hass, "netatmo", {"netatmo": {"client_id": "123", "client_secret": "abc"}}
        )

        await hass.async_block_till_done()

        assert fake_post_hits == 10
        mock_impl.assert_called_once()
        mock_webhook.assert_called_once()

    assert hass.config_entries.async_entries(DOMAIN)
    assert len(hass.states.async_all()) > 0


async def test_setup_component_with_webhook(
    hass: HomeAssistant, config_entry, netatmo_auth
) -> None:
    """Test setup and teardown of the netatmo component with webhook registration."""
    with selected_platforms(["camera", "climate", "light", "sensor"]):
        assert await hass.config_entries.async_setup(config_entry.entry_id)

        await hass.async_block_till_done()

    webhook_id = config_entry.data[CONF_WEBHOOK_ID]
    await simulate_webhook(hass, webhook_id, FAKE_WEBHOOK_ACTIVATION)

    assert len(hass.states.async_all()) > 0

    webhook_id = config_entry.data[CONF_WEBHOOK_ID]
    await simulate_webhook(hass, webhook_id, FAKE_WEBHOOK_ACTIVATION)

    # Assert webhook is established successfully
    climate_entity_livingroom = "climate.livingroom"
    assert hass.states.get(climate_entity_livingroom).state == "auto"
    await simulate_webhook(hass, webhook_id, FAKE_WEBHOOK)
    assert hass.states.get(climate_entity_livingroom).state == "heat"

    for config_entry in hass.config_entries.async_entries("netatmo"):
        await hass.config_entries.async_remove(config_entry.entry_id)

    await hass.async_block_till_done()
    assert len(hass.states.async_all()) == 0
    assert len(hass.config_entries.async_entries(DOMAIN)) == 0


async def test_setup_with_cloud(hass: HomeAssistant, config_entry) -> None:
    """Test if set up with active cloud subscription."""
    await mock_cloud(hass)
    await hass.async_block_till_done()

    with patch(
        "homeassistant.components.cloud.async_is_logged_in", return_value=True
    ), patch(
        "homeassistant.components.cloud.async_is_connected", return_value=True
    ), patch(
        "homeassistant.components.cloud.async_active_subscription", return_value=True
    ), patch(
        "homeassistant.components.cloud.async_create_cloudhook",
        return_value="https://hooks.nabu.casa/ABCD",
    ) as fake_create_cloudhook, patch(
        "homeassistant.components.cloud.async_delete_cloudhook"
    ) as fake_delete_cloudhook, patch(
        "homeassistant.components.netatmo.api.AsyncConfigEntryNetatmoAuth"
    ) as mock_auth, patch(
        "homeassistant.components.netatmo.data_handler.PLATFORMS", []
    ), patch(
        "homeassistant.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
    ), patch(
        "homeassistant.components.netatmo.webhook_generate_url",
    ):
        mock_auth.return_value.async_post_api_request.side_effect = fake_post_request
        assert await async_setup_component(
            hass, "netatmo", {"netatmo": {"client_id": "123", "client_secret": "abc"}}
        )
        assert hass.components.cloud.async_active_subscription() is True
        assert hass.components.cloud.async_is_connected() is True
        fake_create_cloudhook.assert_called_once()

        assert (
            hass.config_entries.async_entries("netatmo")[0].data["cloudhook_url"]
            == "https://hooks.nabu.casa/ABCD"
        )

        await hass.async_block_till_done()
        assert hass.config_entries.async_entries(DOMAIN)

        for config_entry in hass.config_entries.async_entries("netatmo"):
            await hass.config_entries.async_remove(config_entry.entry_id)
            fake_delete_cloudhook.assert_called_once()

        await hass.async_block_till_done()
        assert not hass.config_entries.async_entries(DOMAIN)


async def test_setup_with_cloudhook(hass: HomeAssistant) -> None:
    """Test if set up with active cloud subscription and cloud hook."""
    config_entry = MockConfigEntry(
        domain="netatmo",
        data={
            "auth_implementation": "cloud",
            "cloudhook_url": "https://hooks.nabu.casa/ABCD",
            "token": {
                "refresh_token": "mock-refresh-token",
                "access_token": "mock-access-token",
                "type": "Bearer",
                "expires_in": 60,
                "expires_at": time() + 1000,
                "scope": ALL_SCOPES,
            },
        },
    )
    config_entry.add_to_hass(hass)

    await mock_cloud(hass)
    await hass.async_block_till_done()

    with patch(
        "homeassistant.components.cloud.async_is_logged_in", return_value=True
    ), patch(
        "homeassistant.components.cloud.async_is_connected", return_value=True
    ), patch(
        "homeassistant.components.cloud.async_active_subscription", return_value=True
    ), patch(
        "homeassistant.components.cloud.async_create_cloudhook",
        return_value="https://hooks.nabu.casa/ABCD",
    ) as fake_create_cloudhook, patch(
        "homeassistant.components.cloud.async_delete_cloudhook"
    ) as fake_delete_cloudhook, patch(
        "homeassistant.components.netatmo.api.AsyncConfigEntryNetatmoAuth"
    ) as mock_auth, patch(
        "homeassistant.components.netatmo.data_handler.PLATFORMS", []
    ), patch(
        "homeassistant.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
    ), patch(
        "homeassistant.components.netatmo.webhook_generate_url",
    ):
        mock_auth.return_value.async_post_api_request.side_effect = fake_post_request
        mock_auth.return_value.async_addwebhook.side_effect = AsyncMock()
        mock_auth.return_value.async_dropwebhook.side_effect = AsyncMock()
        assert await async_setup_component(hass, "netatmo", {})
        assert hass.components.cloud.async_active_subscription() is True

        assert (
            hass.config_entries.async_entries("netatmo")[0].data["cloudhook_url"]
            == "https://hooks.nabu.casa/ABCD"
        )

        await hass.async_block_till_done()
        assert hass.config_entries.async_entries(DOMAIN)
        fake_create_cloudhook.assert_not_called()

        for config_entry in hass.config_entries.async_entries("netatmo"):
            await hass.config_entries.async_remove(config_entry.entry_id)
            fake_delete_cloudhook.assert_called_once()

        await hass.async_block_till_done()
        assert not hass.config_entries.async_entries(DOMAIN)


async def test_setup_component_with_delay(hass: HomeAssistant, config_entry) -> None:
    """Test setup of the netatmo component with delayed startup."""
    hass.state = CoreState.not_running

    with patch(
        "pyatmo.AbstractAsyncAuth.async_addwebhook", side_effect=AsyncMock()
    ) as mock_addwebhook, patch(
        "pyatmo.AbstractAsyncAuth.async_dropwebhook", side_effect=AsyncMock()
    ) as mock_dropwebhook, patch(
        "homeassistant.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
    ) as mock_impl, patch(
        "homeassistant.components.netatmo.webhook_generate_url"
    ) as mock_webhook, patch(
        "pyatmo.AbstractAsyncAuth.async_post_api_request", side_effect=fake_post_request
    ) as mock_post_api_request, patch(
        "homeassistant.components.netatmo.data_handler.PLATFORMS", ["light"]
    ):
        assert await async_setup_component(
            hass, "netatmo", {"netatmo": {"client_id": "123", "client_secret": "abc"}}
        )

        await hass.async_block_till_done()

        assert mock_post_api_request.call_count == 7

        mock_impl.assert_called_once()
        mock_webhook.assert_not_called()

        await hass.async_start()
        await hass.async_block_till_done()
        mock_webhook.assert_called_once()

        # Fake webhook activation
        await simulate_webhook(
            hass, config_entry.data[CONF_WEBHOOK_ID], FAKE_WEBHOOK_ACTIVATION
        )
        await hass.async_block_till_done()

        mock_addwebhook.assert_called_once()
        mock_dropwebhook.assert_not_awaited()

        async_fire_time_changed(
            hass,
            dt_util.utcnow() + timedelta(seconds=60),
        )
        await hass.async_block_till_done()

        assert hass.config_entries.async_entries(DOMAIN)
        assert len(hass.states.async_all()) > 0

        await hass.async_stop()
        mock_dropwebhook.assert_called_once()


async def test_setup_component_invalid_token_scope(hass: HomeAssistant) -> None:
    """Test handling of invalid token scope."""
    config_entry = MockConfigEntry(
        domain="netatmo",
        data={
            "auth_implementation": "cloud",
            "token": {
                "refresh_token": "mock-refresh-token",
                "access_token": "mock-access-token",
                "type": "Bearer",
                "expires_in": 60,
                "expires_at": time() + 1000,
                "scope": " ".join(
                    [
                        "read_smokedetector",
                        "read_thermostat",
                        "write_thermostat",
                    ]
                ),
            },
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.netatmo.api.AsyncConfigEntryNetatmoAuth",
    ) as mock_auth, patch(
        "homeassistant.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
    ) as mock_impl, patch(
        "homeassistant.components.netatmo.webhook_generate_url"
    ) as mock_webhook:
        mock_auth.return_value.async_post_api_request.side_effect = fake_post_request
        mock_auth.return_value.async_addwebhook.side_effect = AsyncMock()
        mock_auth.return_value.async_dropwebhook.side_effect = AsyncMock()
        assert await async_setup_component(hass, "netatmo", {})

    await hass.async_block_till_done()

    mock_auth.assert_not_called()
    mock_impl.assert_called_once()
    mock_webhook.assert_not_called()

    assert config_entry.state is config_entries.ConfigEntryState.SETUP_ERROR
    assert hass.config_entries.async_entries(DOMAIN)

    notifications = async_get_persistent_notifications(hass)

    assert len(notifications) > 0

    for config_entry in hass.config_entries.async_entries("netatmo"):
        await hass.config_entries.async_remove(config_entry.entry_id)


async def test_setup_component_invalid_token(hass: HomeAssistant, config_entry) -> None:
    """Test handling of invalid token."""

    async def fake_ensure_valid_token(*args, **kwargs):
        raise aiohttp.ClientResponseError(
            request_info=aiohttp.client.RequestInfo(
                url="http://example.com",
                method="GET",
                headers={},
                real_url="http://example.com",
            ),
            status=400,
            history=(),
        )

    with patch(
        "homeassistant.components.netatmo.api.AsyncConfigEntryNetatmoAuth",
    ) as mock_auth, patch(
        "homeassistant.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
    ) as mock_impl, patch(
        "homeassistant.components.netatmo.webhook_generate_url"
    ) as mock_webhook, patch(
        "homeassistant.helpers.config_entry_oauth2_flow.OAuth2Session"
    ) as mock_session:
        mock_auth.return_value.async_post_api_request.side_effect = fake_post_request
        mock_auth.return_value.async_addwebhook.side_effect = AsyncMock()
        mock_auth.return_value.async_dropwebhook.side_effect = AsyncMock()
        mock_session.return_value.async_ensure_token_valid.side_effect = (
            fake_ensure_valid_token
        )
        assert await async_setup_component(hass, "netatmo", {})

    await hass.async_block_till_done()

    mock_auth.assert_not_called()
    mock_impl.assert_called_once()
    mock_webhook.assert_not_called()

    assert config_entry.state is config_entries.ConfigEntryState.SETUP_ERROR
    assert hass.config_entries.async_entries(DOMAIN)
    notifications = async_get_persistent_notifications(hass)
    assert len(notifications) > 0

    for config_entry in hass.config_entries.async_entries("netatmo"):
        await hass.config_entries.async_remove(config_entry.entry_id)


async def test_unregister_webhook_not_registered(
    hass: HomeAssistant, config_entry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test unregister webhook service when no webhook is registered."""
    async with setup_for_webhook_tests(hass, config_entry) as (
        mock_async_addwebhook,
        mock_async_dropwebhook,
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UNREGISTER_WEBHOOK,
            blocking=True,
        )
        webhook_id = config_entry.data[CONF_WEBHOOK_ID]
        assert not is_webhook_registered(hass, webhook_id)

        mock_async_addwebhook.reset_mock()
        mock_async_dropwebhook.reset_mock()
        mock_async_dropwebhook.side_effect = AsyncMock(side_effect=pyatmo.ApiError)
        caplog.clear()
        assert f"No webhook to be dropped for {webhook_id}" not in caplog.text

        await hass.services.async_call(
            DOMAIN,
            SERVICE_UNREGISTER_WEBHOOK,
            blocking=True,
        )

        mock_async_addwebhook.assert_not_called()
        mock_async_dropwebhook.assert_called_once()

    webhook_id = config_entry.data[CONF_WEBHOOK_ID]
    assert not is_webhook_registered(hass, webhook_id)

    assert f"No webhook to be dropped for {webhook_id}" in caplog.text


async def test_unregister_webhook_drop_error(
    hass: HomeAssistant, config_entry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test unregister webhook service API call to drop webhook fails."""
    async with setup_for_webhook_tests(hass, config_entry) as (
        mock_async_addwebhook,
        mock_async_dropwebhook,
    ):
        mock_async_dropwebhook.side_effect = AsyncMock(side_effect=pyatmo.ApiError)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_UNREGISTER_WEBHOOK,
            blocking=True,
        )

        mock_async_addwebhook.assert_not_called()
        mock_async_dropwebhook.assert_called_once()

    webhook_id = config_entry.data[CONF_WEBHOOK_ID]
    assert not is_webhook_registered(hass, webhook_id)

    assert f"No webhook to be dropped for {webhook_id}" in caplog.text


async def test_unregister_webhook_success(hass: HomeAssistant, config_entry) -> None:
    """Test unregister webhook service API call when expected to succeed."""
    async with setup_for_webhook_tests(hass, config_entry) as (
        mock_async_addwebhook,
        mock_async_dropwebhook,
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UNREGISTER_WEBHOOK,
            blocking=True,
        )

        mock_async_addwebhook.assert_not_called()
        mock_async_dropwebhook.assert_called_once()

    webhook_id = config_entry.data[CONF_WEBHOOK_ID]
    assert not is_webhook_registered(hass, webhook_id)


async def test_register_webhook_https_error(
    hass: HomeAssistant, config_entry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test register webhook service with cloud link and without https."""
    hass.config.components.add("cloud")
    async with setup_for_webhook_tests(hass, config_entry) as (
        mock_async_addwebhook,
        mock_async_dropwebhook,
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UNREGISTER_WEBHOOK,
            blocking=True,
        )
        webhook_id = config_entry.data[CONF_WEBHOOK_ID]
        assert not is_webhook_registered(hass, webhook_id)
        mock_async_addwebhook.reset_mock()
        mock_async_dropwebhook.reset_mock()

        with patch(
            "homeassistant.components.netatmo.webhook_generate_url"
        ) as mock_async_generate_url, pytest.raises(HomeAssistantError) as err:
            mock_async_generate_url.return_value = "http://example.com"
            await hass.services.async_call(
                DOMAIN,
                SERVICE_REGISTER_WEBHOOK,
                blocking=True,
            )

        webhook_id = config_entry.data[CONF_WEBHOOK_ID]
        assert not is_webhook_registered(hass, webhook_id)
        mock_async_addwebhook.assert_not_called()

        assert err.value.translation_domain == DOMAIN
        assert err.value.translation_key == EXCEPTION_ID_WEBHOOK_HTTPS_REQUIRED
        assert (
            "Webhook not registered - HTTPS and port 443 are required to register the webhook"
            in caplog.text
        )


async def test_register_webhook_already_registered(
    hass: HomeAssistant, config_entry
) -> None:
    """Test calling register webhook service when webhook is already registered in Home Assistant."""
    async with setup_for_webhook_tests(hass, config_entry) as (
        mock_async_addwebhook,
        _,
    ):
        webhook_id = config_entry.data[CONF_WEBHOOK_ID]
        assert is_webhook_registered(hass, webhook_id)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_REGISTER_WEBHOOK,
            blocking=True,
        )
        webhook_id = config_entry.data[CONF_WEBHOOK_ID]
        assert is_webhook_registered(hass, webhook_id)
        mock_async_addwebhook.assert_called_once()


async def test_register_webhook_api_error(
    hass: HomeAssistant, config_entry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test calling register webhook service when API errors."""
    async with setup_for_webhook_tests(hass, config_entry) as (
        mock_async_addwebhook,
        _,
    ):
        webhook_id = config_entry.data[CONF_WEBHOOK_ID]
        assert is_webhook_registered(hass, webhook_id)

        error_message = "Test API Error"
        mock_async_addwebhook.side_effect = AsyncMock(
            side_effect=pyatmo.ApiError(error_message)
        )

        with pytest.raises(HomeAssistantError) as err:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_REGISTER_WEBHOOK,
                blocking=True,
            )
        webhook_id = config_entry.data[CONF_WEBHOOK_ID]
        assert is_webhook_registered(hass, webhook_id)
        assert f"Error during webhook registration - {error_message}" in caplog.text

        assert err.value.translation_domain == DOMAIN
        assert err.value.translation_key == EXCEPTION_ID_WEBHOOK_REGISTRATION_FAILED
        assert err.value.translation_placeholders["error"] == error_message


async def test_register_webhook_success(hass: HomeAssistant, config_entry) -> None:
    """Test calling register webhook service when success expected."""
    async with setup_for_webhook_tests(hass, config_entry) as (
        mock_async_addwebhook,
        mock_async_dropwebhook,
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UNREGISTER_WEBHOOK,
            blocking=True,
        )
        webhook_id = config_entry.data[CONF_WEBHOOK_ID]
        assert not is_webhook_registered(hass, webhook_id)
        mock_async_addwebhook.reset_mock()
        mock_async_dropwebhook.reset_mock()

        await hass.services.async_call(
            DOMAIN,
            SERVICE_REGISTER_WEBHOOK,
            blocking=True,
        )
        webhook_id = config_entry.data[CONF_WEBHOOK_ID]
        assert is_webhook_registered(hass, webhook_id)
        mock_async_addwebhook.assert_called_once()
