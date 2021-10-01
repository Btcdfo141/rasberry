"""Test Alexa config."""
import contextlib
from unittest.mock import AsyncMock, Mock, patch

import pytest

from homeassistant.components.cloud import ALEXA_SCHEMA, alexa_config
from homeassistant.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED
from homeassistant.util.dt import utcnow

from tests.common import async_fire_time_changed


@pytest.fixture()
def cloud_stub():
    """Stub the cloud."""
    return Mock(is_logged_in=True, subscription_expired=False)


async def test_alexa_config_expose_entity_prefs(hass, cloud_prefs, cloud_stub):
    """Test Alexa config should expose using prefs."""
    entity_conf = {"should_expose": False}
    await cloud_prefs.async_update(
        alexa_entity_configs={"light.kitchen": entity_conf},
        alexa_default_expose=["light"],
        alexa_enabled=True,
    )
    conf = alexa_config.AlexaConfig(
        hass, ALEXA_SCHEMA({}), "mock-user-id", cloud_prefs, cloud_stub
    )
    await conf.async_initialize()

    assert not conf.should_expose("light.kitchen")
    entity_conf["should_expose"] = True
    assert conf.should_expose("light.kitchen")

    entity_conf["should_expose"] = None
    assert conf.should_expose("light.kitchen")

    assert "alexa" not in hass.config.components
    await cloud_prefs.async_update(
        alexa_default_expose=["sensor"],
    )
    await hass.async_block_till_done()
    assert "alexa" in hass.config.components
    assert not conf.should_expose("light.kitchen")


async def test_alexa_config_report_state(hass, cloud_prefs, cloud_stub):
    """Test Alexa config should expose using prefs."""
    conf = alexa_config.AlexaConfig(
        hass, ALEXA_SCHEMA({}), "mock-user-id", cloud_prefs, cloud_stub
    )
    await conf.async_initialize()

    assert cloud_prefs.alexa_report_state is False
    assert conf.should_report_state is False
    assert conf.is_reporting_states is False

    with patch.object(conf, "async_get_access_token", AsyncMock(return_value="hello")):
        await cloud_prefs.async_update(alexa_report_state=True)
        await hass.async_block_till_done()

    assert cloud_prefs.alexa_report_state is True
    assert conf.should_report_state is True
    assert conf.is_reporting_states is True

    await cloud_prefs.async_update(alexa_report_state=False)
    await hass.async_block_till_done()

    assert cloud_prefs.alexa_report_state is False
    assert conf.should_report_state is False
    assert conf.is_reporting_states is False


async def test_alexa_config_invalidate_token(hass, cloud_prefs, aioclient_mock):
    """Test Alexa config should expose using prefs."""
    aioclient_mock.post(
        "http://example/alexa_token",
        json={
            "access_token": "mock-token",
            "event_endpoint": "http://example.com/alexa_endpoint",
            "expires_in": 30,
        },
    )
    conf = alexa_config.AlexaConfig(
        hass,
        ALEXA_SCHEMA({}),
        "mock-user-id",
        cloud_prefs,
        Mock(
            alexa_access_token_url="http://example/alexa_token",
            auth=Mock(async_check_token=AsyncMock()),
            websession=hass.helpers.aiohttp_client.async_get_clientsession(),
        ),
    )

    token = await conf.async_get_access_token()
    assert token == "mock-token"
    assert len(aioclient_mock.mock_calls) == 1

    token = await conf.async_get_access_token()
    assert token == "mock-token"
    assert len(aioclient_mock.mock_calls) == 1
    assert conf._token_valid is not None
    conf.async_invalidate_access_token()
    assert conf._token_valid is None
    token = await conf.async_get_access_token()
    assert token == "mock-token"
    assert len(aioclient_mock.mock_calls) == 2


@contextlib.contextmanager
def patch_sync_helper():
    """Patch sync helper.

    In Py3.7 this would have been an async context manager.
    """
    to_update = []
    to_remove = []

    def sync_helper(to_upd, to_rem):
        to_update.extend([ent_id for ent_id in to_upd if ent_id not in to_update])
        to_remove.extend([ent_id for ent_id in to_rem if ent_id not in to_remove])
        return True

    with patch("homeassistant.components.cloud.alexa_config.SYNC_DELAY", 0), patch(
        "homeassistant.components.cloud.alexa_config.AlexaConfig._sync_helper",
        side_effect=sync_helper,
    ):
        yield to_update, to_remove


async def test_alexa_update_expose_trigger_sync(hass, cloud_prefs, cloud_stub):
    """Test Alexa config responds to updating exposed entities."""
    await alexa_config.AlexaConfig(
        hass, ALEXA_SCHEMA({}), "mock-user-id", cloud_prefs, cloud_stub
    ).async_initialize()

    with patch_sync_helper() as (to_update, to_remove):
        await cloud_prefs.async_update_alexa_entity_config(
            entity_id="light.kitchen", should_expose=True
        )
        await hass.async_block_till_done()
        async_fire_time_changed(hass, utcnow())
        await hass.async_block_till_done()

    assert to_update == ["light.kitchen"]
    assert to_remove == []

    with patch_sync_helper() as (to_update, to_remove):
        await cloud_prefs.async_update_alexa_entity_config(
            entity_id="light.kitchen", should_expose=False
        )
        await cloud_prefs.async_update_alexa_entity_config(
            entity_id="binary_sensor.door", should_expose=True
        )
        await cloud_prefs.async_update_alexa_entity_config(
            entity_id="sensor.temp", should_expose=True
        )
        await hass.async_block_till_done()
        async_fire_time_changed(hass, utcnow())
        await hass.async_block_till_done()

    assert sorted(to_update) == ["binary_sensor.door", "sensor.temp"]
    assert to_remove == ["light.kitchen"]


async def test_alexa_entity_registry_sync(hass, mock_cloud_login, cloud_prefs):
    """Test Alexa config responds to entity registry."""
    await alexa_config.AlexaConfig(
        hass, ALEXA_SCHEMA({}), "mock-user-id", cloud_prefs, hass.data["cloud"]
    ).async_initialize()

    with patch_sync_helper() as (to_update, to_remove):
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {"action": "create", "entity_id": "light.kitchen"},
        )
        await hass.async_block_till_done()

    assert to_update == ["light.kitchen"]
    assert to_remove == []

    with patch_sync_helper() as (to_update, to_remove):
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {"action": "remove", "entity_id": "light.kitchen"},
        )
        await hass.async_block_till_done()

    assert to_update == []
    assert to_remove == ["light.kitchen"]

    with patch_sync_helper() as (to_update, to_remove):
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {
                "action": "update",
                "entity_id": "light.kitchen",
                "changes": ["entity_id"],
                "old_entity_id": "light.living_room",
            },
        )
        await hass.async_block_till_done()

    assert to_update == ["light.kitchen"]
    assert to_remove == ["light.living_room"]

    with patch_sync_helper() as (to_update, to_remove):
        hass.bus.async_fire(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {"action": "update", "entity_id": "light.kitchen", "changes": ["icon"]},
        )
        await hass.async_block_till_done()

    assert to_update == []
    assert to_remove == []


async def test_alexa_update_report_state(hass, cloud_prefs, cloud_stub):
    """Test Alexa config responds to reporting state."""
    await alexa_config.AlexaConfig(
        hass, ALEXA_SCHEMA({}), "mock-user-id", cloud_prefs, cloud_stub
    ).async_initialize()

    with patch(
        "homeassistant.components.cloud.alexa_config.AlexaConfig.async_sync_entities",
    ) as mock_sync, patch(
        "homeassistant.components.cloud.alexa_config.AlexaConfig.async_enable_proactive_mode",
    ):
        await cloud_prefs.async_update(alexa_report_state=True)
        await hass.async_block_till_done()

    assert len(mock_sync.mock_calls) == 1


def test_enabled_requires_valid_sub(hass, mock_expired_cloud_login, cloud_prefs):
    """Test that alexa config enabled requires a valid Cloud sub."""
    assert cloud_prefs.alexa_enabled
    assert hass.data["cloud"].is_logged_in
    assert hass.data["cloud"].subscription_expired

    config = alexa_config.AlexaConfig(
        hass, ALEXA_SCHEMA({}), "mock-user-id", cloud_prefs, hass.data["cloud"]
    )

    assert not config.enabled


async def test_alexa_handle_logout(hass, cloud_prefs, cloud_stub):
    """Test Alexa config responds to logging out."""
    aconf = alexa_config.AlexaConfig(
        hass, ALEXA_SCHEMA({}), "mock-user-id", cloud_prefs, cloud_stub
    )

    await aconf.async_initialize()

    with patch(
        "homeassistant.components.alexa.config.async_enable_proactive_mode",
        return_value=Mock(),
    ) as mock_enable:
        await aconf.async_enable_proactive_mode()

    # This will trigger a prefs update when we logout.
    await cloud_prefs.get_cloud_user()

    cloud_stub.is_logged_in = False
    with patch.object(
        cloud_stub.auth,
        "async_check_token",
        side_effect=AssertionError("Should not be called"),
    ):
        await cloud_prefs.async_set_username(None)
        await hass.async_block_till_done()

    assert len(mock_enable.return_value.mock_calls) == 1
