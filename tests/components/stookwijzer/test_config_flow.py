"""Tests for the Stookwijzer config flow."""
from unittest.mock import patch

from homeassistant.components.stookwijzer.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_user_flow(hass: HomeAssistant) -> None:
    """Test the full user configuration flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == SOURCE_USER
    assert "flow_id" in result

    with patch(
        "homeassistant.components.stookwijzer.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_LOCATION: {
                    CONF_LATITUDE: 1.0,
                    CONF_LONGITUDE: 1.1,
                }
            },
        )

    assert result2.get("type") == FlowResultType.CREATE_ENTRY
    assert result2.get("data") == {
        "location": {
            "latitude": 1.0,
            "longitude": 1.1,
        },
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_already_configured(hass: HomeAssistant) -> None:
    """Test we abort if the Stookwijzer location is already configured."""
    MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_LOCATION: {
                CONF_LATITUDE: 2.0,
                CONF_LONGITUDE: 2.1,
            }
        },
        unique_id="2.0-2.1",
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert "flow_id" in result

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_LOCATION: {
                CONF_LATITUDE: 2.0,
                CONF_LONGITUDE: 2.1,
            }
        },
    )

    assert result2.get("type") == FlowResultType.ABORT
    assert result2.get("reason") == "already_configured"
