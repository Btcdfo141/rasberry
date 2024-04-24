"""Tests for the Lektrico Charging Station config flow."""

import dataclasses
from ipaddress import ip_address

from lektricowifi import DeviceConnectionError

from homeassistant import config_entries
from homeassistant.components.lektrico.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    ATTR_HW_VERSION,
    ATTR_SERIAL_NUMBER,
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_TYPE,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import (
    MOCKED_DEVICE_BAD_ID_ZEROCONF_DATA,
    MOCKED_DEVICE_BAD_NO_ID_ZEROCONF_DATA,
    MOCKED_DEVICE_BOARD_REV,
    MOCKED_DEVICE_FRIENDLY_NAME,
    MOCKED_DEVICE_IP_ADDRESS,
    MOCKED_DEVICE_SERIAL_NUMBER,
    MOCKED_DEVICE_SERIAL_NUMBER_FOR_3EM,
    MOCKED_DEVICE_SERIAL_NUMBER_FOR_EM,
    MOCKED_DEVICE_TYPE,
    MOCKED_DEVICE_TYPE_FOR_3EM,
    MOCKED_DEVICE_TYPE_FOR_EM,
    MOCKED_DEVICE_ZEROCONF_DATA,
    MOCKED_DEVICE_ZEROCONF_DATA_FOR_3EM,
    MOCKED_DEVICE_ZEROCONF_DATA_FOR_EM,
)

from tests.common import MockConfigEntry


async def test_user_setup(
    hass: HomeAssistant, mock_device_config, mock_setup_entry
) -> None:
    """Test manually setting up."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER
    assert "flow_id" in result

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
            CONF_FRIENDLY_NAME: MOCKED_DEVICE_FRIENDLY_NAME,
        },
    )
    await hass.async_block_till_done()

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert (
        result.get("title")
        == f"{MOCKED_DEVICE_FRIENDLY_NAME} ({MOCKED_DEVICE_SERIAL_NUMBER})"
    )
    assert result.get("data") == {
        CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
        CONF_FRIENDLY_NAME: MOCKED_DEVICE_FRIENDLY_NAME,
        ATTR_SERIAL_NUMBER: MOCKED_DEVICE_SERIAL_NUMBER,
        CONF_TYPE: MOCKED_DEVICE_TYPE,
        ATTR_HW_VERSION: MOCKED_DEVICE_BOARD_REV,
    }
    assert "result" in result
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_setup_already_exists(
    hass: HomeAssistant, mock_device_config
) -> None:
    """Test manually setting up when the device already exists."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
            CONF_FRIENDLY_NAME: MOCKED_DEVICE_FRIENDLY_NAME,
        },
        unique_id=MOCKED_DEVICE_SERIAL_NUMBER,
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert not result["errors"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
            CONF_FRIENDLY_NAME: MOCKED_DEVICE_FRIENDLY_NAME,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_setup_device_offline(
    hass: HomeAssistant, mock_device_config
) -> None:
    """Test manually setting up when device is offline."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert not result["errors"]

    mock_device_config.side_effect = DeviceConnectionError
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
            CONF_FRIENDLY_NAME: MOCKED_DEVICE_FRIENDLY_NAME,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == "form"
    assert result["errors"] == {CONF_HOST: "cannot_connect"}


async def test_discovered_zeroconf(
    hass: HomeAssistant, mock_device_config, mock_setup_entry
) -> None:
    """Test we can setup when discovered from zeroconf."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCKED_DEVICE_ZEROCONF_DATA,
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"] == {
        CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
        CONF_FRIENDLY_NAME: MOCKED_DEVICE_TYPE,
        ATTR_SERIAL_NUMBER: MOCKED_DEVICE_SERIAL_NUMBER,
        CONF_TYPE: MOCKED_DEVICE_TYPE,
        ATTR_HW_VERSION: MOCKED_DEVICE_BOARD_REV,
    }
    assert result2["title"] == f"{MOCKED_DEVICE_TYPE} ({MOCKED_DEVICE_SERIAL_NUMBER})"

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    zc_data_new_ip = dataclasses.replace(MOCKED_DEVICE_ZEROCONF_DATA)
    zc_data_new_ip.ip_address = ip_address(MOCKED_DEVICE_IP_ADDRESS)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=zc_data_new_ip,
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == MOCKED_DEVICE_IP_ADDRESS

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCKED_DEVICE_BAD_ID_ZEROCONF_DATA,
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "missing_underline_in_id"

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCKED_DEVICE_BAD_NO_ID_ZEROCONF_DATA,
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "missing_id"


async def test_discovered_zeroconf_device_connection_error(
    hass: HomeAssistant, mock_device_config
) -> None:
    """Test we can setup when discovered from zeroconf but device went offline."""

    mock_device_config.side_effect = DeviceConnectionError
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCKED_DEVICE_ZEROCONF_DATA,
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "cannot_connect"}


async def test_discovered_zeroconf_EM(
    hass: HomeAssistant, mock_device_config_for_em, mock_setup_entry
) -> None:
    """Test we can setup when EM discovered from zeroconf."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCKED_DEVICE_ZEROCONF_DATA_FOR_EM,
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"] == {
        CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
        CONF_FRIENDLY_NAME: MOCKED_DEVICE_TYPE_FOR_EM,
        ATTR_SERIAL_NUMBER: MOCKED_DEVICE_SERIAL_NUMBER_FOR_EM,
        CONF_TYPE: MOCKED_DEVICE_TYPE_FOR_EM,
        ATTR_HW_VERSION: MOCKED_DEVICE_BOARD_REV,
    }
    assert (
        result2["title"]
        == f"{MOCKED_DEVICE_TYPE_FOR_EM} ({MOCKED_DEVICE_SERIAL_NUMBER_FOR_EM})"
    )


async def test_discovered_zeroconf_3EM(
    hass: HomeAssistant, mock_device_config_for_3em, mock_setup_entry
) -> None:
    """Test we can setup when 3EM discovered from zeroconf."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCKED_DEVICE_ZEROCONF_DATA_FOR_3EM,
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"] == {
        CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
        CONF_FRIENDLY_NAME: MOCKED_DEVICE_TYPE_FOR_3EM,
        ATTR_SERIAL_NUMBER: MOCKED_DEVICE_SERIAL_NUMBER_FOR_3EM,
        CONF_TYPE: MOCKED_DEVICE_TYPE_FOR_3EM,
        ATTR_HW_VERSION: MOCKED_DEVICE_BOARD_REV,
    }
    assert (
        result2["title"]
        == f"{MOCKED_DEVICE_TYPE_FOR_3EM} ({MOCKED_DEVICE_SERIAL_NUMBER_FOR_3EM})"
    )
