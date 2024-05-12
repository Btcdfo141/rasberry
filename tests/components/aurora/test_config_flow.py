"""Test the Aurora config flow."""

from unittest.mock import patch, AsyncMock

from aiohttp import ClientError

from homeassistant import config_entries
from homeassistant.components.aurora.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

DATA = {
    "latitude": -10,
    "longitude": 10.2,
}


async def test_full_flow(hass: HomeAssistant, mock_setup_entry: AsyncMock, mock_aurora_client: AsyncMock) -> None:
    """Test full flow."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        DATA,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Aurora visibility"
    assert result["data"] == DATA
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass: HomeAssistant, mock_setup_entry: AsyncMock, mock_aurora_client: AsyncMock) -> None:
    """Test if invalid response or no connection returned from the API."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "homeassistant.components.aurora.config_flow.AuroraForecast.get_forecast_data",
        side_effect=ClientError,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            DATA,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_with_unknown_error(hass: HomeAssistant) -> None:
    """Test with unknown error response from the API."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.aurora.config_flow.AuroraForecast.get_forecast_data",
        side_effect=Exception,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            DATA,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "unknown"}


async def test_option_flow(hass: HomeAssistant) -> None:
    """Test option flow."""
    entry = MockConfigEntry(domain=DOMAIN, data=DATA)
    entry.add_to_hass(hass)

    assert not entry.options

    with patch("homeassistant.components.aurora.async_setup_entry", return_value=True):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        result = await hass.config_entries.options.async_init(
            entry.entry_id,
            data=None,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"forecast_threshold": 65},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["forecast_threshold"] == 65
