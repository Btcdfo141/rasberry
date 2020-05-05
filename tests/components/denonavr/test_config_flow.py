"""Test the DenonAVR config flow."""
from tests.async_mock import patch

import pytest

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.components.denonavr.config_flow import (
    CONF_RECEIVER_ID,
    CONF_SHOW_ALL_SOURCES,
    CONF_ZONE2,
    CONF_ZONE3,
    DEFAULT_SHOW_SOURCES,
    DEFAULT_TIMEOUT,
    DEFAULT_ZONE2,
    DEFAULT_ZONE3,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_TIMEOUT

TEST_HOST = "1.2.3.4"
TEST_HOST2 = "5.6.7.8"
TEST_NAME = "Test_Receiver"
TEST_MODEL = "model5"
TEST_SERIALNUMBER = "123456789"
TEST_MANUFACTURER = "Denon"
TEST_SSDP_LOCATION = f"http://{TEST_HOST}/"
TEST_UNIQUE_ID = f"{TEST_MODEL}-{TEST_SERIALNUMBER}"
TEST_DISCOVER_1_RECEIVER = [{CONF_HOST: TEST_HOST}]
TEST_DISCOVER_2_RECEIVER = [{CONF_HOST: TEST_HOST}, {CONF_HOST: TEST_HOST2}]


@pytest.fixture(name="denonavr_connect", autouse=True)
def denonavr_connect_fixture():
    """Mock denonavr connection and entry setup."""
    with patch(
        "homeassistant.components.denonavr.receiver.denonavr.DenonAVR._update_input_func_list",
        return_value=True,
    ), patch(
        "homeassistant.components.denonavr.receiver.denonavr.DenonAVR._get_receiver_name",
        return_value=TEST_NAME,
    ), patch(
        "homeassistant.components.denonavr.receiver.denonavr.DenonAVR._get_support_sound_mode",
        return_value=True,
    ), patch(
        "homeassistant.components.denonavr.receiver.denonavr.DenonAVR._update_avr_2016",
        return_value=True,
    ), patch(
        "homeassistant.components.denonavr.receiver.denonavr.DenonAVR._update_avr",
        return_value=True,
    ), patch(
        "homeassistant.components.denonavr.receiver.denonavr.DenonAVR.get_device_info",
        return_value=True,
    ), patch(
        "homeassistant.components.denonavr.receiver.denonavr.DenonAVR.name", TEST_NAME,
    ), patch(
        "homeassistant.components.denonavr.receiver.denonavr.DenonAVR.model_name",
        TEST_MODEL,
    ), patch(
        "homeassistant.components.denonavr.receiver.denonavr.DenonAVR.serial_number",
        TEST_SERIALNUMBER,
    ), patch(
        "homeassistant.components.denonavr.async_setup_entry", return_value=True
    ):
        yield


async def test_config_flow_manual_host_success(hass):
    """Test a successful config flow manualy initialized by the user with the host specified."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: TEST_HOST},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "settings"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {},)

    assert result["type"] == "create_entry"
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_TIMEOUT: DEFAULT_TIMEOUT,
        CONF_SHOW_ALL_SOURCES: DEFAULT_SHOW_SOURCES,
        CONF_ZONE2: DEFAULT_ZONE2,
        CONF_ZONE3: DEFAULT_ZONE3,
        CONF_RECEIVER_ID: TEST_UNIQUE_ID,
    }


async def test_config_flow_manual_discover_1_success(hass):
    """Test a successful config flow manualy initialized by the user without the host specified and 1 receiver discovered."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.denonavr.config_flow.denonavr.ssdp.identify_denonavr_receivers",
        return_value=TEST_DISCOVER_1_RECEIVER,
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {},)

    assert result["type"] == "form"
    assert result["step_id"] == "settings"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {},)

    assert result["type"] == "create_entry"
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_TIMEOUT: DEFAULT_TIMEOUT,
        CONF_SHOW_ALL_SOURCES: DEFAULT_SHOW_SOURCES,
        CONF_ZONE2: DEFAULT_ZONE2,
        CONF_ZONE3: DEFAULT_ZONE3,
        CONF_RECEIVER_ID: TEST_UNIQUE_ID,
    }


async def test_config_flow_manual_discover_2_success(hass):
    """Test a successful config flow manualy initialized by the user without the host specified and 2 receivers discovered."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.denonavr.config_flow.denonavr.ssdp.identify_denonavr_receivers",
        return_value=TEST_DISCOVER_2_RECEIVER,
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {},)

    assert result["type"] == "form"
    assert result["step_id"] == "select"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"select_host": TEST_HOST2},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "settings"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {},)

    assert result["type"] == "create_entry"
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST2,
        CONF_TIMEOUT: DEFAULT_TIMEOUT,
        CONF_SHOW_ALL_SOURCES: DEFAULT_SHOW_SOURCES,
        CONF_ZONE2: DEFAULT_ZONE2,
        CONF_ZONE3: DEFAULT_ZONE3,
        CONF_RECEIVER_ID: TEST_UNIQUE_ID,
    }


async def test_config_flow_manual_discover_error(hass):
    """Test a failed config flow manualy initialized by the user without the host specified and no receivers discovered."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.denonavr.config_flow.denonavr.ssdp.identify_denonavr_receivers",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {},)

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "discovery_error"}


async def test_config_flow_settings(hass):
    """Test a succesfull config flow manualy initialized by the user with the host specified and non default settings specified."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: TEST_HOST},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "settings"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_TIMEOUT: 5,
            CONF_SHOW_ALL_SOURCES: True,
            CONF_ZONE2: True,
            CONF_ZONE3: True,
        },
    )

    assert result["type"] == "create_entry"
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_TIMEOUT: 5,
        CONF_SHOW_ALL_SOURCES: True,
        CONF_ZONE2: True,
        CONF_ZONE3: True,
        CONF_RECEIVER_ID: TEST_UNIQUE_ID,
    }


async def test_config_flow_manual_host_connection_error(hass):
    """Test a failed config flow manualy initialized by the user with the host specified and a connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: TEST_HOST},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "settings"

    with patch(
        "homeassistant.components.denonavr.receiver.denonavr.DenonAVR.get_device_info",
        side_effect=ConnectionError,
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {},)

    assert result["type"] == "abort"
    assert result["reason"] == "connection_error"


async def test_config_flow_ssdp(hass):
    """Test a succesfull config flow initialized by ssdp discovery."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data={
            ssdp.ATTR_UPNP_MANUFACTURER: TEST_MANUFACTURER,
            ssdp.ATTR_UPNP_MODEL_NAME: TEST_MODEL,
            ssdp.ATTR_UPNP_SERIAL: TEST_SERIALNUMBER,
            ssdp.ATTR_SSDP_LOCATION: TEST_SSDP_LOCATION,
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "settings"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {},)

    assert result["type"] == "create_entry"
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_TIMEOUT: DEFAULT_TIMEOUT,
        CONF_SHOW_ALL_SOURCES: DEFAULT_SHOW_SOURCES,
        CONF_ZONE2: DEFAULT_ZONE2,
        CONF_ZONE3: DEFAULT_ZONE3,
        CONF_RECEIVER_ID: TEST_UNIQUE_ID,
    }


async def test_config_flow_ssdp_not_denon(hass):
    """Test a failed config flow initialized by ssdp discovery with a not supported manufacturer."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data={
            ssdp.ATTR_UPNP_MANUFACTURER: "NotSupported",
            ssdp.ATTR_UPNP_MODEL_NAME: TEST_MODEL,
            ssdp.ATTR_UPNP_SERIAL: TEST_SERIALNUMBER,
            ssdp.ATTR_SSDP_LOCATION: TEST_SSDP_LOCATION,
        },
    )

    assert result["type"] == "abort"
    assert result["reason"] == "not_denonavr_manufacturer"


async def test_config_flow_ssdp_missing_info(hass):
    """Test a failed config flow initialized by ssdp discovery with missing information."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data={
            ssdp.ATTR_UPNP_MANUFACTURER: TEST_MANUFACTURER,
            ssdp.ATTR_SSDP_LOCATION: TEST_SSDP_LOCATION,
        },
    )

    assert result["type"] == "abort"
    assert result["reason"] == "not_denonavr_missing"
