"""Define tests for the Brother Printer config flow."""

from ipaddress import ip_address
import json
from unittest.mock import patch

from brother import SnmpError, UnsupportedModelError
import pytest

from homeassistant.components import zeroconf
from homeassistant.components.brother.const import DOMAIN
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    SOURCE_USER,
    SOURCE_ZEROCONF,
)
from homeassistant.const import CONF_HOST, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry, load_fixture

CONFIG = {CONF_HOST: "127.0.0.1", CONF_TYPE: "laser"}
PRINTER_DATA = json.loads(load_fixture("printer_data.json", "brother"))

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_show_form(hass: HomeAssistant) -> None:
    """Test that the form is served with no input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_create_entry_with_hostname(hass: HomeAssistant) -> None:
    """Test that the user step works with printer hostname."""
    with (
        patch("brother.Brother.initialize"),
        patch(
            "brother.Brother._get_data",
            return_value=PRINTER_DATA,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={CONF_HOST: "example.local", CONF_TYPE: "laser"},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "HL-L2340DW 0123456789"
        assert result["data"][CONF_HOST] == "example.local"
        assert result["data"][CONF_TYPE] == "laser"


async def test_create_entry_with_ipv4_address(hass: HomeAssistant) -> None:
    """Test that the user step works with printer IPv4 address."""
    with (
        patch("brother.Brother.initialize"),
        patch(
            "brother.Brother._get_data",
            return_value=PRINTER_DATA,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "HL-L2340DW 0123456789"
        assert result["data"][CONF_HOST] == "127.0.0.1"
        assert result["data"][CONF_TYPE] == "laser"


async def test_create_entry_with_ipv6_address(hass: HomeAssistant) -> None:
    """Test that the user step works with printer IPv6 address."""
    with (
        patch("brother.Brother.initialize"),
        patch(
            "brother.Brother._get_data",
            return_value=PRINTER_DATA,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={CONF_HOST: "2001:db8::1428:57ab", CONF_TYPE: "laser"},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "HL-L2340DW 0123456789"
        assert result["data"][CONF_HOST] == "2001:db8::1428:57ab"
        assert result["data"][CONF_TYPE] == "laser"


async def test_invalid_hostname(hass: HomeAssistant) -> None:
    """Test invalid hostname in user_input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_HOST: "invalid/hostname", CONF_TYPE: "laser"},
    )

    assert result["errors"] == {CONF_HOST: "wrong_host"}


@pytest.mark.parametrize("exc", [ConnectionError, TimeoutError])
async def test_connection_error(hass: HomeAssistant, exc: Exception) -> None:
    """Test connection to host error."""
    with (
        patch("brother.Brother.initialize"),
        patch("brother.Brother._get_data", side_effect=exc),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["errors"] == {"base": "cannot_connect"}


async def test_snmp_error(hass: HomeAssistant) -> None:
    """Test SNMP error."""
    with (
        patch("brother.Brother.initialize"),
        patch("brother.Brother._get_data", side_effect=SnmpError("error")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["errors"] == {"base": "snmp_error"}


async def test_unsupported_model_error(hass: HomeAssistant) -> None:
    """Test unsupported printer model error."""
    with (
        patch("brother.Brother.initialize"),
        patch("brother.Brother._get_data", side_effect=UnsupportedModelError("error")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "unsupported_model"


async def test_device_exists_abort(hass: HomeAssistant) -> None:
    """Test we abort config flow if Brother printer already configured."""
    with (
        patch("brother.Brother.initialize"),
        patch(
            "brother.Brother._get_data",
            return_value=PRINTER_DATA,
        ),
    ):
        MockConfigEntry(domain=DOMAIN, unique_id="0123456789", data=CONFIG).add_to_hass(
            hass
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


@pytest.mark.parametrize("exc", [ConnectionError, TimeoutError, SnmpError("error")])
async def test_zeroconf_exception(hass: HomeAssistant, exc: Exception) -> None:
    """Test we abort zeroconf flow on exception."""
    with (
        patch("brother.Brother.initialize"),
        patch("brother.Brother._get_data", side_effect=exc),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data=zeroconf.ZeroconfServiceInfo(
                ip_address=ip_address("127.0.0.1"),
                ip_addresses=[ip_address("127.0.0.1")],
                hostname="example.local.",
                name="Brother Printer",
                port=None,
                properties={},
                type="mock_type",
            ),
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "cannot_connect"


async def test_zeroconf_unsupported_model(hass: HomeAssistant) -> None:
    """Test unsupported printer model error."""
    with (
        patch("brother.Brother.initialize"),
        patch("brother.Brother._get_data") as mock_get_data,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data=zeroconf.ZeroconfServiceInfo(
                ip_address=ip_address("127.0.0.1"),
                ip_addresses=[ip_address("127.0.0.1")],
                hostname="example.local.",
                name="Brother Printer",
                port=None,
                properties={"product": "MFC-8660DN"},
                type="mock_type",
            ),
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "unsupported_model"
        assert len(mock_get_data.mock_calls) == 0


async def test_zeroconf_device_exists_abort(hass: HomeAssistant) -> None:
    """Test we abort zeroconf flow if Brother printer already configured."""
    with (
        patch("brother.Brother.initialize"),
        patch(
            "brother.Brother._get_data",
            return_value=PRINTER_DATA,
        ),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id="0123456789",
            data={CONF_HOST: "example.local", CONF_TYPE: "laser"},
        )
        entry.add_to_hass(hass)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data=zeroconf.ZeroconfServiceInfo(
                ip_address=ip_address("127.0.0.1"),
                ip_addresses=[ip_address("127.0.0.1")],
                hostname="example.local.",
                name="Brother Printer",
                port=None,
                properties={},
                type="mock_type",
            ),
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"

    # Test config entry got updated with latest IP
    assert entry.data["host"] == "127.0.0.1"


async def test_zeroconf_no_probe_existing_device(hass: HomeAssistant) -> None:
    """Test we do not probe the device is the host is already configured."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="0123456789", data=CONFIG)
    entry.add_to_hass(hass)
    with (
        patch("brother.Brother.initialize"),
        patch("brother.Brother._get_data") as mock_get_data,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data=zeroconf.ZeroconfServiceInfo(
                ip_address=ip_address("127.0.0.1"),
                ip_addresses=[ip_address("127.0.0.1")],
                hostname="example.local.",
                name="Brother Printer",
                port=None,
                properties={},
                type="mock_type",
            ),
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert len(mock_get_data.mock_calls) == 0


async def test_zeroconf_confirm_create_entry(hass: HomeAssistant) -> None:
    """Test zeroconf confirmation and create config entry."""
    with (
        patch("brother.Brother.initialize"),
        patch(
            "brother.Brother._get_data",
            return_value=PRINTER_DATA,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data=zeroconf.ZeroconfServiceInfo(
                ip_address=ip_address("127.0.0.1"),
                ip_addresses=[ip_address("127.0.0.1")],
                hostname="example.local.",
                name="Brother Printer",
                port=None,
                properties={},
                type="mock_type",
            ),
        )

        assert result["step_id"] == "zeroconf_confirm"
        assert result["description_placeholders"]["model"] == "HL-L2340DW"
        assert result["description_placeholders"]["serial_number"] == "0123456789"
        assert result["type"] is FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_TYPE: "laser"}
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "HL-L2340DW 0123456789"
        assert result["data"][CONF_HOST] == "127.0.0.1"
        assert result["data"][CONF_TYPE] == "laser"


async def test_reconfigure_successful(hass: HomeAssistant) -> None:
    """Test starting a reconfigure flow."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="0123456789", data=CONFIG)
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
        data=entry.data,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure_confirm"

    with (
        patch("brother.Brother.initialize"),
        patch(
            "brother.Brother._get_data",
            return_value=PRINTER_DATA,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HOST: "10.10.10.10"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {
        CONF_HOST: "10.10.10.10",
        CONF_TYPE: "laser",
    }


@pytest.mark.parametrize(
    ("exc", "base_error"),
    [
        (ConnectionError, "cannot_connect"),
        (TimeoutError, "cannot_connect"),
        (SnmpError("error"), "snmp_error"),
    ],
)
async def test_reconfigurewith_exception(
    hass: HomeAssistant, exc: Exception, base_error: str
) -> None:
    """Test starting a reconfigure flow but exception is reised."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="0123456789", data=CONFIG)
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
        data=entry.data,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure_confirm"

    with (
        patch("brother.Brother.initialize"),
        patch("brother.Brother._get_data", side_effect=exc),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HOST: "10.10.10.10"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure_confirm"
    assert result["errors"] == {"base": base_error}

    with (
        patch("brother.Brother.initialize"),
        patch(
            "brother.Brother._get_data",
            return_value=PRINTER_DATA,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HOST: "10.10.10.10"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {
        CONF_HOST: "10.10.10.10",
        CONF_TYPE: "laser",
    }


async def test_reconfigure_invalid_hostname(hass: HomeAssistant) -> None:
    """Test starting a reconfigure flow but no connection found."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="0123456789", data=CONFIG)
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
        data=entry.data,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: "invalid/hostname"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure_confirm"
    assert result["errors"] == {CONF_HOST: "wrong_host"}


async def test_reconfigure_another_device(hass: HomeAssistant) -> None:
    """Test starting the reconfiguration process, but with another printer."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="xyz012", data=CONFIG)
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
        data=entry.data,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure_confirm"

    with (
        patch("brother.Brother.initialize"),
        patch(
            "brother.Brother._get_data",
            return_value=PRINTER_DATA,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HOST: "10.10.10.10"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "another_device"
