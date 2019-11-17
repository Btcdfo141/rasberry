"""Tests for Samsung TV config flow."""
from asynctest import mock
import pytest
from samsungctl.exceptions import AccessDenied, UnhandledResponse
from unittest.mock import patch

from homeassistant.components.samsungtv.const import (
    CONF_MANUFACTURER,
    CONF_MODEL,
    DOMAIN,
)
from homeassistant.components.ssdp import (
    ATTR_HOST,
    ATTR_NAME,
    ATTR_MODEL_NAME,
    ATTR_MANUFACTURER,
    ATTR_UDN,
)
from homeassistant.const import CONF_HOST, CONF_ID, CONF_NAME

MOCK_USER_DATA = {CONF_HOST: "fake_host", CONF_NAME: "fake_name"}
MOCK_SSDP_DATA = {
    ATTR_HOST: "fake_host",
    ATTR_NAME: "[TV]fake_name",
    ATTR_MANUFACTURER: "fake_manufacturer",
    ATTR_MODEL_NAME: "fake_model",
    ATTR_UDN: "uuid:fake_uuid",
}
MOCK_SSDP_DATA_NOPREFIX = {
    ATTR_HOST: "fake2_host",
    ATTR_NAME: "fake2_name",
    ATTR_MANUFACTURER: "fake2_manufacturer",
    ATTR_MODEL_NAME: "fake2_model",
    ATTR_UDN: "fake2_uuid",
}


@pytest.fixture(name="remote")
def remote_fixture():
    """Patch the samsungctl Remote."""
    with patch("samsungctl.Remote") as remote_class, patch(
        "homeassistant.components.samsungtv.config_flow.socket"
    ) as socket_class:
        remote = mock.Mock()
        remote_class.return_value = remote
        socket = mock.Mock()
        socket_class.return_value = socket
        yield remote


async def test_user(hass, remote):
    """Test starting a flow by user."""

    # entry was added
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=MOCK_USER_DATA
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "fake_name"
    assert result["data"][CONF_HOST] == "fake_host"
    assert result["data"][CONF_NAME] is None
    assert result["data"][CONF_MANUFACTURER] is None
    assert result["data"][CONF_MODEL] is None
    assert result["data"][CONF_ID] is None


async def test_user_empty(hass, remote):
    """Test starting a flow by user."""

    # show form
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert len(result["errors"]) == 0


async def test_user_error(hass, remote):
    """Test starting a flow by user with errors."""

    # both input fields missing
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={}
    )
    assert result["type"] == "form"
    assert len(result["errors"]) == 2
    assert result["errors"][CONF_HOST] is not None
    assert result["errors"][CONF_NAME] is not None

    # CONF_NAME input field missing
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={CONF_HOST: "test"}
    )
    assert result["type"] == "form"
    assert len(result["errors"]) == 1
    assert result["errors"][CONF_NAME] is not None


async def test_user_missing_auth(hass):
    """Test starting a flow from discovery with authentication."""
    with patch(
        "homeassistant.components.samsungtv.config_flow.Remote",
        side_effect=AccessDenied("Boom"),
    ), patch("homeassistant.components.samsungtv.config_flow.socket"):

        # missing authentication
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=MOCK_USER_DATA
        )
        assert result["type"] == "abort"
        assert result["reason"] == "auth_missing"


async def test_user_not_supported(hass):
    """Test starting a flow from discovery for not supported device."""
    with patch(
        "homeassistant.components.samsungtv.config_flow.Remote",
        side_effect=UnhandledResponse("Boom"),
    ), patch("homeassistant.components.samsungtv.config_flow.socket"):

        # device not supported
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=MOCK_USER_DATA
        )
        assert result["type"] == "abort"
        assert result["reason"] == "not_supported"


async def test_user_not_found(hass):
    """Test starting a flow from discovery but no device found."""
    with patch(
        "homeassistant.components.samsungtv.config_flow.Remote",
        side_effect=OSError("Boom"),
    ), patch("homeassistant.components.samsungtv.config_flow.socket"):

        # device not found
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=MOCK_USER_DATA
        )
        assert result["type"] == "abort"
        assert result["reason"] == "not_found"


async def test_ssdp(hass, remote):
    """Test starting a flow from discovery."""

    # confirm to add the entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "ssdp"}, data=MOCK_SSDP_DATA
    )
    assert result["type"] == "form"
    assert result["step_id"] == "confirm"

    # entry was added
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input="whatever"
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "fake_name (fake_model)"
    assert result["data"][CONF_HOST] == "fake_host"
    assert result["data"][CONF_NAME] == "fake_name"
    assert result["data"][CONF_MANUFACTURER] == "fake_manufacturer"
    assert result["data"][CONF_MODEL] == "fake_model"
    assert result["data"][CONF_ID] == "fake_uuid"


async def test_ssdp_noprefix(hass, remote):
    """Test starting a flow from discovery without prefixes."""

    # confirm to add the entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "ssdp"}, data=MOCK_SSDP_DATA_NOPREFIX
    )
    assert result["type"] == "form"
    assert result["step_id"] == "confirm"

    # entry was added
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input="whatever"
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "fake2_name (fake2_model)"
    assert result["data"][CONF_HOST] == "fake2_host"
    assert result["data"][CONF_NAME] == "fake2_name"
    assert result["data"][CONF_MANUFACTURER] == "fake2_manufacturer"
    assert result["data"][CONF_MODEL] == "fake2_model"
    assert result["data"][CONF_ID] == "fake2_uuid"


async def test_ssdp_missing_auth(hass):
    """Test starting a flow from discovery with authentication."""
    with patch(
        "homeassistant.components.samsungtv.config_flow.Remote",
        side_effect=AccessDenied("Boom"),
    ), patch("homeassistant.components.samsungtv.config_flow.socket"):

        # confirm to add the entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "ssdp"}, data=MOCK_SSDP_DATA
        )
        assert result["type"] == "form"
        assert result["step_id"] == "confirm"

        # missing authentication
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input="whatever"
        )
        assert result["type"] == "abort"
        assert result["reason"] == "auth_missing"


async def test_ssdp_not_supported(hass):
    """Test starting a flow from discovery for not supported device."""
    with patch(
        "homeassistant.components.samsungtv.config_flow.Remote",
        side_effect=UnhandledResponse("Boom"),
    ), patch("homeassistant.components.samsungtv.config_flow.socket"):

        # confirm to add the entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "ssdp"}, data=MOCK_SSDP_DATA
        )
        assert result["type"] == "form"
        assert result["step_id"] == "confirm"

        # device not supported
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input="whatever"
        )
        assert result["type"] == "abort"
        assert result["reason"] == "not_supported"


async def test_ssdp_not_found(hass):
    """Test starting a flow from discovery but no device found."""
    with patch(
        "homeassistant.components.samsungtv.config_flow.Remote",
        side_effect=OSError("Boom"),
    ), patch("homeassistant.components.samsungtv.config_flow.socket"):

        # confirm to add the entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "ssdp"}, data=MOCK_SSDP_DATA
        )
        assert result["type"] == "form"
        assert result["step_id"] == "confirm"

        # device not found
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input="whatever"
        )
        assert result["type"] == "abort"
        assert result["reason"] == "not_found"


async def test_discovery_already_in_progress(hass, remote):
    """Test starting a flow from discovery twice."""

    # confirm to add the entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "ssdp"}, data=MOCK_SSDP_DATA
    )
    assert result["type"] == "form"
    assert result["step_id"] == "confirm"

    # failed as already in progress
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "ssdp"}, data=MOCK_SSDP_DATA
    )
    assert result["type"] == "abort"
    assert result["reason"] == "already_in_progress"


async def test_discovery_already_configured(hass, remote):
    """Test starting a flow from discovery when already configured."""

    # entry was added
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=MOCK_USER_DATA
    )
    assert result["type"] == "create_entry"

    # failed as already configured
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "ssdp"}, data=MOCK_SSDP_DATA
    )
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
