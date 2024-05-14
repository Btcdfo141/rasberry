"""Test the Aquacell config flow."""

from unittest.mock import AsyncMock

from aioaquacell import ApiException, AuthenticationFailed
import pytest

from homeassistant.components.aquacell.const import CONF_REFRESH_TOKEN, DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.components.aquacell import TEST_CONFIG_ENTRY, TEST_USER_INPUT

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_form(
    hass: HomeAssistant, mock_setup_entry: AsyncMock, mock_aquacell_api: AsyncMock
) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        TEST_USER_INPUT,
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == TEST_CONFIG_ENTRY[CONF_EMAIL]
    assert result2["data"][CONF_EMAIL] == TEST_CONFIG_ENTRY[CONF_EMAIL]
    assert result2["data"][CONF_PASSWORD] == TEST_CONFIG_ENTRY[CONF_PASSWORD]
    assert result2["data"][CONF_REFRESH_TOKEN] == TEST_CONFIG_ENTRY[CONF_REFRESH_TOKEN]
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (ApiException, "cannot_connect"),
        (AuthenticationFailed, "invalid_auth"),
        (Exception, "unknown"),
    ],
)
async def test_form_exceptions(
    hass: HomeAssistant,
    exception: Exception,
    error: str,
    mock_setup_entry: AsyncMock,
    mock_aquacell_api: AsyncMock,
) -> None:
    """Test we handle form exceptions."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    mock_aquacell_api.authenticate.side_effect = exception
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], TEST_USER_INPUT
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": error}

    mock_aquacell_api.authenticate.side_effect = None

    result3 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        TEST_USER_INPUT,
    )
    await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == TEST_CONFIG_ENTRY[CONF_EMAIL]
    assert result3["data"][CONF_EMAIL] == TEST_CONFIG_ENTRY[CONF_EMAIL]
    assert result3["data"][CONF_PASSWORD] == TEST_CONFIG_ENTRY[CONF_PASSWORD]
    assert result3["data"][CONF_REFRESH_TOKEN] == TEST_CONFIG_ENTRY[CONF_REFRESH_TOKEN]
    assert len(mock_setup_entry.mock_calls) == 1
