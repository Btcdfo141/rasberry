"""Test the myIO config flow."""
from asynctest import patch

from homeassistant import config_entries, data_entry_flow, setup
from homeassistant.components.myio.config_flow import (
    AppPortProblem,
    CannotConnect,
    InvalidAuth,
)
from homeassistant.components.myio.const import DOMAIN

TEST_DATA = {
    "name": "myIO-Server",
    "host": "192.168.1.170",
    "username": "admin",
    "password": "admin",
    "port": 80,
    "port_app": 843,
}


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.myio.config_flow.MyIOHub.authenticate",
        return_value=True,
    ), patch(
        "homeassistant.components.myio.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.myio.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], TEST_DATA
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "myIO-Server"
    assert result2["data"] == TEST_DATA
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.myio.config_flow.MyIOHub.authenticate",
        side_effect=InvalidAuth,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "myIO Server",
                "host": "192.168.1.170",
                "username": "ad",
                "password": "adm",
                "port": 80,
                "port_app": 843,
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.myio.config_flow.MyIOHub.authenticate",
        side_effect=CannotConnect,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "myIO Server",
                "host": "192.168.1.171",
                "username": "admin",
                "password": "admin",
                "port": 81,
                "port_app": 841,
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_app_port_problem(hass):
    """Test we handle application port error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.myio.config_flow.MyIOHub.authenticate",
        side_effect=AppPortProblem,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "myIO Server",
                "host": "192.168.1.170",
                "username": "admin",
                "password": "admin",
                "port": 80,
                "port_app": 841,
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "app_port"}


async def test_form_validate(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.myio.config_flow.validate_input",
        return_value=True,
    ), patch(
        "homeassistant.components.myio.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.myio.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], TEST_DATA
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "myIO-Server"
    assert result2["data"] == TEST_DATA
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_validate_invalid_auth(hass):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.myio.config_flow.validate_input",
        side_effect=InvalidAuth,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "myIO Server",
                "host": "192.168.1.170",
                "username": "ad",
                "password": "adm",
                "port": 80,
                "port_app": 843,
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_validate_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.myio.config_flow.validate_input",
        side_effect=CannotConnect,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "myIO Server",
                "host": "192.168.1.171",
                "username": "admin",
                "password": "admin",
                "port": 81,
                "port_app": 841,
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_validate_app_port_problem(hass):
    """Test we handle application port error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.myio.config_flow.validate_input",
        side_effect=AppPortProblem,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "myIO Server",
                "host": "192.168.1.170",
                "username": "admin",
                "password": "admin",
                "port": 80,
                "port_app": 841,
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "app_port"}


async def test_form_already_configured(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.myio.config_flow.MyIOHub.authenticate",
        return_value=True,
    ), patch(
        "homeassistant.components.myio.config_flow.MyIOHub.already_check",
        return_value=True,
    ), patch(
        "homeassistant.components.myio.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.myio.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], TEST_DATA
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "myIO-Server"
    assert result2["data"] == TEST_DATA
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_already_configured_False(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.myio.config_flow.MyIOHub.authenticate",
        return_value=True,
    ), patch(
        "homeassistant.components.myio.config_flow.MyIOHub.already_check",
        return_value=False,
    ), patch(
        "homeassistant.components.myio.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.myio.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], TEST_DATA
        )

    assert result2["type"] == "form"
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 0
    assert len(mock_setup_entry.mock_calls) == 0
