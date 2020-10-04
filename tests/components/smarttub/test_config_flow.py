"""Test the smarttub config flow."""
import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.smarttub.const import DEFAULT_SCAN_INTERVAL, DOMAIN
from homeassistant.const import CONF_SCAN_INTERVAL

from tests.async_mock import patch
from tests.common import MockConfigEntry


@pytest.fixture
def mock_controller():
    """Mock the controller."""
    with patch(
        "homeassistant.components.smarttub.config_flow.SmartTubController",
        autospec=True,
    ) as controller_class_mock:
        controller_mock = controller_class_mock.return_value
        controller_mock.get_account_id.return_value = "account-id1"
        yield controller_mock


async def test_form(hass, mock_controller):
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.smarttub.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.smarttub.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"email": "test-email", "password": "test-password"},
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "test-email"
    assert result2["data"] == {
        "email": "test-email",
        "password": "test-password",
    }
    await hass.async_block_till_done()
    mock_setup.assert_called_once()
    mock_setup_entry.assert_called_once()
    mock_controller.get_account_id.assert_called()


async def test_form_invalid_auth(hass, mock_controller):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_controller.get_account_id.return_value = None

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"email": "test-email", "password": "test-password"},
    )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_options(hass, mock_controller, config_data):
    """Test config flow options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        options={},
    )
    config_entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.smarttub.async_setup", return_value=True
    ), patch(
        "homeassistant.components.smarttub.async_setup_entry",
        return_value=True,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.options == {}

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options[CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL
