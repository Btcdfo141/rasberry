"""Define tests for the Eufy Security config flow."""
import eufy_security
import pytest

from homeassistant import data_entry_flow
from homeassistant.components.eufy_security import DOMAIN, config_flow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from tests.common import MockConfigEntry, MockDependency, mock_coro


@pytest.fixture
def mock_client_coro():
    """Define a fixture for a API object creation coroutine."""
    return mock_coro()


@pytest.fixture
def mock_eufy_security(mock_client_coro):
    """Mock the aionotion library."""
    with MockDependency("aionotion") as mock_:
        mock_.async_login.return_value = mock_client_coro
        yield mock_


async def test_duplicate_error(hass):
    """Test that errors are shown when duplicates are added."""
    conf = {CONF_USERNAME: "user@host.com", CONF_PASSWORD: "password123"}

    MockConfigEntry(domain=DOMAIN, data=conf).add_to_hass(hass)
    flow = config_flow.EufySecurityFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user(user_input=conf)
    assert result["errors"] == {CONF_USERNAME: "identifier_exists"}


@pytest.mark.parametrize(
    "mock_client_coro", [mock_coro(exception=eufy_security.errors.EufySecurityError)]
)
async def test_invalid_credentials(hass, mock_eufy_security):
    """Test that an invalid API/App Key throws an error."""
    conf = {CONF_USERNAME: "user@host.com", CONF_PASSWORD: "password123"}

    flow = config_flow.EufySecurityFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user(user_input=conf)
    assert result["errors"] == {"base": "invalid_credentials"}


async def test_show_form(hass):
    """Test that the form is served with no input."""
    flow = config_flow.EufySecurityFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user(user_input=None)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"


async def test_step_import(hass, mock_eufy_security):
    """Test that the import step works."""
    conf = {CONF_USERNAME: "user@host.com", CONF_PASSWORD: "password123"}

    flow = config_flow.EufySecurityFlowHandler()
    flow.hass = hass

    result = await flow.async_step_import(import_config=conf)
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "user@host.com"
    assert result["data"] == {
        CONF_USERNAME: "user@host.com",
        CONF_PASSWORD: "password123",
    }


async def test_step_user(hass, mock_eufy_security):
    """Test that the user step works."""
    conf = {CONF_USERNAME: "user@host.com", CONF_PASSWORD: "password123"}

    flow = config_flow.EufySecurityFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user(user_input=conf)
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "user@host.com"
    assert result["data"] == {
        CONF_USERNAME: "user@host.com",
        CONF_PASSWORD: "password123",
    }
