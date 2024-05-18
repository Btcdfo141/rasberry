"""Test the Transport for London config flow."""
from unittest.mock import AsyncMock, Mock, patch
from urllib.error import HTTPError

import pytest

from homeassistant import config_entries
from homeassistant.components.tfl.config_flow import (
    STEP_STOP_POINT_DATA_SCHEMA,
    CannotConnect,
    ConfigFlow,
    InvalidAuth,
)
from homeassistant.components.tfl.const import (
    CONF_API_APP_KEY,
    CONF_STOP_POINT,
    CONF_STOP_POINT_ADD_ANOTHER,
    CONF_STOP_POINTS,
    DOMAIN,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_flow_user_init(hass: HomeAssistant) -> None:
    """Test the initialization of the form in the first step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["handler"] == "tfl"
    assert result["errors"] == {}


async def test_flow_stops_form_is_shown(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test the initialization of the form in the second step of the config flow."""
    user_config_flow_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert user_config_flow_result["type"] == FlowResultType.FORM
    assert user_config_flow_result["errors"] == {}

    with patch(
        "homeassistant.components.tfl.config_flow.stopPoint.getCategories",
        return_value={},
    ):
        stops_config_flow__init_result = await hass.config_entries.flow.async_configure(
            user_config_flow_result["flow_id"],
            user_input={CONF_API_APP_KEY: "appy_appy_app_key"},
        )
        await hass.async_block_till_done()

    # Validate that the stops form is shown
    assert stops_config_flow__init_result["type"] == FlowResultType.FORM
    assert stops_config_flow__init_result["step_id"] == "stop_point"
    assert stops_config_flow__init_result["handler"] == "tfl"
    assert stops_config_flow__init_result["errors"] == {}
    assert stops_config_flow__init_result["data_schema"] == STEP_STOP_POINT_DATA_SCHEMA


@patch("homeassistant.components.tfl.config_flow.stopPoint")
async def test_flow_stops_does_more_stops(m_stopPoint, hass: HomeAssistant) -> None:
    """Test that the stops step allows for more stops to be entered."""

    m_stop_point_api = Mock()
    m_stop_point_api.getStationArrivals = Mock()
    m_stopPoint.return_value = m_stop_point_api

    ConfigFlow.data = {
        CONF_API_APP_KEY: "appy_appy_app_key",
        CONF_STOP_POINTS: [],
    }
    with patch(
        "homeassistant.components.tfl.config_flow.stopPoint.getStationArrivals",
        return_value={},
    ):
        stops_config_flow_init_result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "stop_point"}
        )
        await hass.async_block_till_done()

    with patch("homeassistant.components.tfl.async_setup_entry", return_value=True):
        stops_config_flow_again_result = await hass.config_entries.flow.async_configure(
            stops_config_flow_init_result["flow_id"],
            user_input={
                CONF_STOP_POINT: "AAAAAAAA1",
                CONF_STOP_POINT_ADD_ANOTHER: True,
            },
        )

    # Validate that the stops form was returned again
    assert stops_config_flow_again_result["type"] == FlowResultType.FORM
    assert stops_config_flow_again_result["step_id"] == "stop_point"
    assert stops_config_flow_again_result["handler"] == "tfl"
    assert stops_config_flow_again_result["errors"] == {}
    assert stops_config_flow_again_result["data_schema"] == STEP_STOP_POINT_DATA_SCHEMA

    with patch("homeassistant.components.tfl.async_setup_entry", return_value=True):
        stops_config_success_result = await hass.config_entries.flow.async_configure(
            stops_config_flow_init_result["flow_id"],
            user_input={
                CONF_STOP_POINT: "AAAAAAAA2",
            },
        )

    # assert expected == stops_config_success_result
    assert stops_config_success_result["type"] == FlowResultType.CREATE_ENTRY
    assert stops_config_success_result["handler"] == "tfl"
    assert stops_config_success_result["title"] == "Transport for London"
    assert stops_config_success_result["data"] == {
        CONF_API_APP_KEY: "appy_appy_app_key",
        CONF_STOP_POINTS: ["AAAAAAAA1", "AAAAAAAA2"],
    }
    assert stops_config_success_result["version"] == 1


@patch("homeassistant.components.tfl.config_flow.stopPoint")
async def test_flow_stops_creates_config_entry(
    m_stopPoint, hass: HomeAssistant
) -> None:
    """Test the Config Entry is successfully created."""
    m_stop_point_api = Mock()
    m_stop_point_api.getStationArrivals = Mock()
    m_stopPoint.return_value = m_stop_point_api

    ConfigFlow.data = {
        CONF_API_APP_KEY: "appy_appy_app_key",
        CONF_STOP_POINTS: [],
    }
    with patch(
        "homeassistant.components.tfl.config_flow.stopPoint.getStationArrivals",
        return_value={},
    ):
        stops_config_flow_init_result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "stop_point"}
        )
        await hass.async_block_till_done()

    with patch("homeassistant.components.tfl.async_setup_entry", return_value=True):
        stops_config_success_result = await hass.config_entries.flow.async_configure(
            stops_config_flow_init_result["flow_id"],
            user_input={CONF_STOP_POINT: "AAAAAAAA1"},
        )

    # Validate that config entry was created
    assert stops_config_success_result["type"] == FlowResultType.CREATE_ENTRY
    assert stops_config_success_result["handler"] == "tfl"
    assert stops_config_success_result["title"] == "Transport for London"
    assert stops_config_success_result["data"] == {
        CONF_API_APP_KEY: "appy_appy_app_key",
        CONF_STOP_POINTS: ["AAAAAAAA1"],
    }
    assert stops_config_success_result["version"] == 1


@patch("homeassistant.components.tfl.config_flow.stopPoint")
async def test_form_no_stop(m_stopPoint, hass: HomeAssistant) -> None:
    """Test we handle no stops being entered."""
    m_stop_point_api = Mock()
    m_stop_point_api.getStationArrivals = Mock()
    m_stopPoint.return_value = m_stop_point_api

    ConfigFlow.data = {
        CONF_API_APP_KEY: "appy_appy_app_key",
        CONF_STOP_POINTS: [],
    }
    with patch(
        "homeassistant.components.tfl.config_flow.stopPoint.getStationArrivals",
        return_value={},
    ):
        stops_config_flow_init_result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "stop_point"}
        )
        await hass.async_block_till_done()

    with patch("homeassistant.components.tfl.async_setup_entry", return_value=True):
        stops_config_error_result = await hass.config_entries.flow.async_configure(
            stops_config_flow_init_result["flow_id"],
        )

    assert stops_config_error_result["type"] == FlowResultType.FORM
    assert stops_config_error_result["step_id"] == "stop_point"
    assert stops_config_error_result["handler"] == "tfl"
    assert stops_config_error_result["errors"] == {}
    assert stops_config_error_result["data_schema"] == STEP_STOP_POINT_DATA_SCHEMA


@patch("homeassistant.components.tfl.config_flow.stopPoint")
async def test_invalid_stop_id(m_stopPoint, hass: HomeAssistant) -> None:
    """Test we handle an invalid stop id being entered."""
    m_stop_point_api = Mock()
    m_stop_point_api.getStationArrivals = Mock(
        side_effect=HTTPError("http://test", 404, "Not Found", None, None)
    )
    m_stopPoint.return_value = m_stop_point_api

    ConfigFlow.data = {
        CONF_API_APP_KEY: "appy_appy_app_key",
        CONF_STOP_POINTS: [],
    }
    with patch(
        "homeassistant.components.tfl.config_flow.stopPoint.getStationArrivals",
        return_value={},
    ):
        stops_config_flow_init_result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "stop_point"}
        )
        await hass.async_block_till_done()

    with patch("homeassistant.components.tfl.async_setup_entry", return_value=True):
        stops_config_error_result = await hass.config_entries.flow.async_configure(
            stops_config_flow_init_result["flow_id"],
            user_input={CONF_STOP_POINT: "DOES_NOT_EXIST"},
        )

    assert stops_config_error_result["type"] == FlowResultType.FORM
    assert stops_config_error_result["step_id"] == "stop_point"
    assert stops_config_error_result["handler"] == "tfl"
    assert stops_config_error_result["errors"] == {"base": "invalid_stop_point"}
    assert stops_config_error_result["data_schema"] == STEP_STOP_POINT_DATA_SCHEMA


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""
    user_form_init_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.tfl.config_flow.validate_app_key",
        side_effect=InvalidAuth,
    ):
        user_form_error_result = await hass.config_entries.flow.async_configure(
            user_form_init_result["flow_id"],
            user_input={
                CONF_API_APP_KEY: "appy_appy_app_key",
            },
        )

    assert user_form_error_result["type"] == FlowResultType.FORM
    assert user_form_error_result["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    user_form_init_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.tfl.config_flow.validate_app_key",
        side_effect=CannotConnect,
    ):
        user_form_error_result = await hass.config_entries.flow.async_configure(
            user_form_init_result["flow_id"],
            user_input={CONF_API_APP_KEY: "appy_appy_app_key"},
        )

    assert user_form_error_result["type"] == FlowResultType.FORM
    assert user_form_error_result["errors"] == {"base": "cannot_connect"}


async def test_options_flow_init(hass: HomeAssistant) -> None:
    """Test that the options flow is successfully initialised."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="unique_id",
        data={
            CONF_API_APP_KEY: "appy_appy_app_key",
            CONF_STOP_POINTS: ["AAAAAAAA1"],
        },
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # show initial form
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert {} == result["errors"]
    assert result["data_schema"]({})["app_key"] == "appy_appy_app_key"
    assert ["AAAAAAAA1"] == result["data_schema"].schema[CONF_STOP_POINTS].options


async def test_options_flow_change_app_key(hass: HomeAssistant) -> None:
    """Test that the options flow allows for the app key to be changed."""

    options_form_init_result = await setup_options_flow_with_init_result(hass)

    with patch("homeassistant.components.tfl.async_setup_entry", return_value=True):
        options_form_result = await hass.config_entries.options.async_configure(
            options_form_init_result["flow_id"],
            user_input={
                CONF_API_APP_KEY: "appy_appy_app_key_version_2",
            },
        )

    assert options_form_result["type"] == FlowResultType.CREATE_ENTRY
    assert options_form_result["title"] == "Transport for London"
    assert options_form_result["data"] == {
        CONF_API_APP_KEY: "appy_appy_app_key_version_2",
        CONF_STOP_POINTS: ["AAAAAAAA1", "BBBBBBBB2"],
    }
    assert options_form_result["version"] == 1


async def test_options_flow_replace_stop(hass: HomeAssistant) -> None:
    """Test that the options flow allows for a stop to be replaced."""

    options_form_init_result = await setup_options_flow_with_init_result(hass)

    with patch("homeassistant.components.tfl.async_setup_entry", return_value=True):
        options_form_result = await hass.config_entries.options.async_configure(
            options_form_init_result["flow_id"],
            user_input={CONF_STOP_POINTS: ["AAAAAAAA1"], CONF_STOP_POINT: "CCCCCCCC3"},
        )

    assert options_form_result["type"] == FlowResultType.CREATE_ENTRY
    assert options_form_result["title"] == "Transport for London"
    assert options_form_result["data"] == {
        CONF_API_APP_KEY: "appy_appy_app_key",
        CONF_STOP_POINTS: ["AAAAAAAA1", "CCCCCCCC3"],
    }
    assert options_form_result["version"] == 1


async def test_options_flow_add_stop(hass: HomeAssistant) -> None:
    """Test that the options flow allows for a stop to be added."""
    options_form_init_result = await setup_options_flow_with_init_result(hass)

    with patch("homeassistant.components.tfl.async_setup_entry", return_value=True):
        options_form_result = await hass.config_entries.options.async_configure(
            options_form_init_result["flow_id"],
            user_input={
                CONF_STOP_POINTS: ["AAAAAAAA1", "BBBBBBBB2"],
                CONF_STOP_POINT: "CCCCCCCC3",
            },
        )

    assert options_form_result["type"] == FlowResultType.CREATE_ENTRY
    assert options_form_result["title"] == "Transport for London"
    assert options_form_result["data"] == {
        CONF_API_APP_KEY: "appy_appy_app_key",
        CONF_STOP_POINTS: ["AAAAAAAA1", "BBBBBBBB2", "CCCCCCCC3"],
    }
    assert options_form_result["version"] == 1


async def test_options_flow_remove_stop(hass: HomeAssistant) -> None:
    """Test that the options flow allows for a stop to be removed."""
    options_form_init_result = await setup_options_flow_with_init_result(hass)

    with patch("homeassistant.components.tfl.async_setup_entry", return_value=True):
        options_form_result = await hass.config_entries.options.async_configure(
            options_form_init_result["flow_id"],
            user_input={CONF_STOP_POINTS: ["AAAAAAAA1"]},
        )

    assert options_form_result["type"] == FlowResultType.CREATE_ENTRY
    assert options_form_result["title"] == "Transport for London"
    assert options_form_result["data"] == {
        CONF_API_APP_KEY: "appy_appy_app_key",
        CONF_STOP_POINTS: ["AAAAAAAA1"],
    }
    assert options_form_result["version"] == 1


async def setup_options_flow_with_init_result(hass: HomeAssistant):
    """Create the config entry, setup the options flow, and return the init result."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="unique_id",
        data={
            CONF_API_APP_KEY: "appy_appy_app_key",
            CONF_STOP_POINTS: ["AAAAAAAA1", "BBBBBBBB2"],
        },
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    options_form_init_result = await hass.config_entries.options.async_init(
        config_entry.entry_id
    )
    return options_form_init_result
