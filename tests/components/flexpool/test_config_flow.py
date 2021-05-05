"""Test the Flexpool config flow."""
from unittest.mock import patch

from homeassistant import config_entries, setup
from homeassistant.components.flexpool.const import DOMAIN
from homeassistant.exceptions import HomeAssistantError


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    with patch(
        "homeassistant.components.flexpool.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "address": "0xf98bc863ad9d5dc6415360251ca6f793efc3c390",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "0xf98bc863ad9d5dc6415360251ca6f793efc3c390"
    assert result2["data"] == {
        "address": "0xf98bc863ad9d5dc6415360251ca6f793efc3c390",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_address(hass):
    """Test we get the form with an invalid address."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "address": "0xf98bc863ad9d5dc6415360251ca6f793efc3c39X",
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_address"}


async def test_form_unknown_error(hass):
    """Test validation with intentionally unknown error."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.flexpool.config_flow.validate_input",
        side_effect=HomeAssistantError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "address": "0xf98bc863ad9d5dc6415360251ca6f793efc3c390",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "unknown"}
