"""Test the Hydrawise config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from requests.exceptions import ConnectTimeout, HTTPError

from homeassistant import config_entries
from homeassistant.components.hydrawise.const import DOMAIN
from homeassistant.const import CONF_API_KEY, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


@patch("hydrawiser.core.Hydrawiser")
async def test_form(
    mock_api: MagicMock, hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_key": "abc123"}
    )
    mock_api.return_value.status = "All good!"
    mock_api.return_value.customer_id = 12345
    await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Hydrawise"
    assert result2["data"] == {"api_key": "abc123"}
    assert len(mock_setup_entry.mock_calls) == 1


@patch("hydrawiser.core.Hydrawiser", side_effect=HTTPError)
async def test_form_api_error(mock_api: MagicMock, hass: HomeAssistant) -> None:
    """Test we handle API errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_key": "abc123"}
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


@patch("hydrawiser.core.Hydrawiser", side_effect=ConnectTimeout)
async def test_form_connect_timeout(mock_api: MagicMock, hass: HomeAssistant) -> None:
    """Test we handle API errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_key": "abc123"}
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "timeout_connect"}


@patch("hydrawiser.core.Hydrawiser")
async def test_form_no_status(mock_api: MagicMock, hass: HomeAssistant) -> None:
    """Test we handle API errors."""
    mock_api.return_value.status = None
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_key": "abc123"}
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


@patch("hydrawiser.core.Hydrawiser")
async def test_flow_import_success(mock_api: MagicMock, hass: HomeAssistant) -> None:
    """Test that we can import a YAML config."""
    mock_api.return_value.status = "All good!"
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            CONF_API_KEY: "__api_key__",
            CONF_SCAN_INTERVAL: 120,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Hydrawise"
    assert result["data"] == {
        CONF_API_KEY: "__api_key__",
    }


@patch("hydrawiser.core.Hydrawiser")
async def test_flow_import_already_imported(
    mock_api: MagicMock, hass: HomeAssistant
) -> None:
    """Test that we can handle a YAML config already imported."""
    mock_config_entry = MockConfigEntry(
        title="Hydrawise",
        domain=DOMAIN,
        data={
            CONF_API_KEY: "__api_key__",
        },
    )
    mock_config_entry.add_to_hass(hass)

    mock_api.return_value.status = "All good!"
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            CONF_API_KEY: "__api_key__",
            CONF_SCAN_INTERVAL: 120,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result.get("reason") == "already_configured"
