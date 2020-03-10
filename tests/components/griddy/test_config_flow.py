"""Test the Griddy Power config flow."""
from asynctest import MagicMock, patch

from homeassistant import config_entries, setup
from homeassistant.components.griddy.config_flow import CannotConnect
from homeassistant.components.griddy.const import DOMAIN


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "griddypower.async_api.AsyncGriddy.async_getnow", return_value=MagicMock(),
    ), patch(
        "homeassistant.components.griddy.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.griddy.async_setup_entry", return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"loadzone": "LZ_HOUSTON"},
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Load Zone LZ_HOUSTON"
    assert result2["data"] == {"loadzone": "LZ_HOUSTON"}
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.griddy.config_flow.GriddyGateway.async_verify_connection",
        side_effect=CannotConnect,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"loadzone": "LZ_NORTH"},
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}
