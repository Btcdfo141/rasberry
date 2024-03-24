"""Tests for the AirGradient config flow."""
from ipaddress import ip_address
from unittest.mock import AsyncMock

from airgradient import AirGradientConnectionError
import pytest

from homeassistant.components import zeroconf
from homeassistant.components.airgradient import DOMAIN
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

ZEROCONF_DISCOVERY = zeroconf.ZeroconfServiceInfo(
    ip_address=ip_address("10.0.0.131"),
    ip_addresses=[ip_address("10.0.0.131")],
    hostname="mock_hostname",
    name="12345",
    port=None,
    type="_airgradient._tcp.local.",
    properties={},
)


async def test_full_flow(
    hass: HomeAssistant,
    mock_airgradient_client: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test full flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "10.0.0.131"},
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "84fce612f5b8"
    assert result["data"] == {
        CONF_HOST: "10.0.0.131",
    }
    assert result["result"].unique_id == "84fce612f5b8"


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (AirGradientConnectionError(), "cannot_connect"),
        (Exception(), "unknown"),
    ],
)
async def test_flow_errors(
    hass: HomeAssistant,
    mock_airgradient_client: AsyncMock,
    mock_setup_entry: AsyncMock,
    side_effect: Exception,
    error: str,
) -> None:
    """Test flow errors."""
    mock_airgradient_client.get_status.side_effect = side_effect

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "10.0.0.131"},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_airgradient_client.get_status.side_effect = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "10.0.0.131"},
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_duplicate(
    hass: HomeAssistant,
    mock_airgradient_client: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test duplicate flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "10.0.0.131"},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zeroconf_flow(
    hass: HomeAssistant,
    mock_airgradient_client: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test zeroconf flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=ZEROCONF_DISCOVERY,
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "84fce612f5b8"
    assert result["data"] == {
        CONF_HOST: "10.0.0.131",
    }
    assert result["result"].unique_id == "84fce612f5b8"
