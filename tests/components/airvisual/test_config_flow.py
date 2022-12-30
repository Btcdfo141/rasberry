"""Define tests for the AirVisual config flow."""
from unittest.mock import Mock, patch

from pyairvisual.cloud_api import (
    InvalidKeyError,
    KeyExpiredError,
    NotFoundError,
    UnauthorizedError,
)
from pyairvisual.errors import AirVisualError
import pytest

from homeassistant import data_entry_flow
from homeassistant.components.airvisual import (
    CONF_CITY,
    CONF_COUNTRY,
    CONF_GEOGRAPHIES,
    CONF_INTEGRATION_TYPE,
    DOMAIN,
    INTEGRATION_TYPE_GEOGRAPHY_COORDS,
    INTEGRATION_TYPE_GEOGRAPHY_NAME,
    INTEGRATION_TYPE_NODE_PRO,
)
from homeassistant.components.airvisual_pro import DOMAIN as AIRVISUAL_PRO_DOMAIN
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.const import (
    CONF_API_KEY,
    CONF_IP_ADDRESS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PASSWORD,
    CONF_SHOW_ON_MAP,
    CONF_STATE,
)
from homeassistant.helpers import device_registry as dr, issue_registry as ir

from tests.common import MockConfigEntry


async def test_duplicate_error(hass, config, config_entry, data, setup_airvisual):
    """Test that errors are shown when duplicate entries are added."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={"type": INTEGRATION_TYPE_GEOGRAPHY_COORDS},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=config
    )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "data,exc,errors,integration_type",
    [
        (
            {
                CONF_API_KEY: "abcde12345",
                CONF_CITY: "Beijing",
                CONF_STATE: "Beijing",
                CONF_COUNTRY: "China",
            },
            InvalidKeyError,
            {CONF_API_KEY: "invalid_api_key"},
            INTEGRATION_TYPE_GEOGRAPHY_NAME,
        ),
        (
            {
                CONF_API_KEY: "abcde12345",
                CONF_CITY: "Beijing",
                CONF_STATE: "Beijing",
                CONF_COUNTRY: "China",
            },
            KeyExpiredError,
            {CONF_API_KEY: "invalid_api_key"},
            INTEGRATION_TYPE_GEOGRAPHY_NAME,
        ),
        (
            {
                CONF_API_KEY: "abcde12345",
                CONF_CITY: "Beijing",
                CONF_STATE: "Beijing",
                CONF_COUNTRY: "China",
            },
            UnauthorizedError,
            {CONF_API_KEY: "invalid_api_key"},
            INTEGRATION_TYPE_GEOGRAPHY_NAME,
        ),
        (
            {
                CONF_API_KEY: "abcde12345",
                CONF_CITY: "Beijing",
                CONF_STATE: "Beijing",
                CONF_COUNTRY: "China",
            },
            NotFoundError,
            {CONF_CITY: "location_not_found"},
            INTEGRATION_TYPE_GEOGRAPHY_NAME,
        ),
        (
            {
                CONF_API_KEY: "abcde12345",
                CONF_CITY: "Beijing",
                CONF_STATE: "Beijing",
                CONF_COUNTRY: "China",
            },
            AirVisualError,
            {"base": "unknown"},
            INTEGRATION_TYPE_GEOGRAPHY_NAME,
        ),
    ],
)
async def test_errors(hass, data, exc, errors, integration_type):
    """Test that an exceptions show an error."""
    with patch("pyairvisual.air_quality.AirQuality.city", side_effect=exc):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={"type": integration_type}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=data
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] == errors


@pytest.mark.parametrize(
    "config,config_entry_version,unique_id",
    [
        (
            {
                CONF_API_KEY: "abcde12345",
                CONF_GEOGRAPHIES: [
                    {CONF_LATITUDE: 51.528308, CONF_LONGITUDE: -0.3817765},
                    {
                        CONF_CITY: "Beijing",
                        CONF_STATE: "Beijing",
                        CONF_COUNTRY: "China",
                    },
                ],
            },
            1,
            "abcde12345",
        )
    ],
)
async def test_migration_1_2(hass, config, config_entry, setup_airvisual, unique_id):
    """Test migrating from version 1 to 2."""
    config_entries = hass.config_entries.async_entries(DOMAIN)
    assert len(config_entries) == 2

    assert config_entries[0].unique_id == "51.528308, -0.3817765"
    assert config_entries[0].title == "Cloud API (51.528308, -0.3817765)"
    assert config_entries[0].data == {
        CONF_API_KEY: "abcde12345",
        CONF_LATITUDE: 51.528308,
        CONF_LONGITUDE: -0.3817765,
        CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_GEOGRAPHY_COORDS,
    }

    assert config_entries[1].unique_id == "Beijing, Beijing, China"
    assert config_entries[1].title == "Cloud API (Beijing, Beijing, China)"
    assert config_entries[1].data == {
        CONF_API_KEY: "abcde12345",
        CONF_CITY: "Beijing",
        CONF_STATE: "Beijing",
        CONF_COUNTRY: "China",
        CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_GEOGRAPHY_NAME,
    }


async def test_migration_2_3(hass, pro):
    """Test migrating from version 2 to 3."""
    old_pro_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100",
        data={
            CONF_IP_ADDRESS: "192.168.1.100",
            CONF_PASSWORD: "abcde12345",
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_NODE_PRO,
        },
        version=2,
    )
    old_pro_entry.add_to_hass(hass)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        name="192.168.1.100",
        config_entry_id=old_pro_entry.entry_id,
        identifiers={(DOMAIN, "ABCDE12345")},
    )

    with patch(
        "homeassistant.components.airvisual.automation.automations_with_device",
        return_value=["automation.test_automation"],
    ), patch(
        "homeassistant.components.airvisual.async_get_pro_device_by_config_entry",
        return_value=Mock(id="abcde12345"),
    ), patch(
        "homeassistant.components.airvisual_pro.NodeSamba", return_value=pro
    ), patch(
        "homeassistant.components.airvisual_pro.config_flow.NodeSamba", return_value=pro
    ):
        await hass.config_entries.async_setup(old_pro_entry.entry_id)
        await hass.async_block_till_done()

        for domain, entry_count in ((DOMAIN, 0), (AIRVISUAL_PRO_DOMAIN, 1)):
            entries = hass.config_entries.async_entries(domain)
            assert len(entries) == entry_count

        issue_registry = ir.async_get(hass)
        assert len(issue_registry.issues) == 1


async def test_options_flow(hass, config_entry):
    """Test config flow options."""
    with patch(
        "homeassistant.components.airvisual.async_setup_entry", return_value=True
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        result = await hass.config_entries.options.async_init(config_entry.entry_id)

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={CONF_SHOW_ON_MAP: False}
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert config_entry.options == {CONF_SHOW_ON_MAP: False}


async def test_step_geography_by_coords(hass, config, setup_airvisual):
    """Test setting up a geography entry by latitude/longitude."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={"type": INTEGRATION_TYPE_GEOGRAPHY_COORDS},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=config
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Cloud API (51.528308, -0.3817765)"
    assert result["data"] == {
        CONF_API_KEY: "abcde12345",
        CONF_LATITUDE: 51.528308,
        CONF_LONGITUDE: -0.3817765,
        CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_GEOGRAPHY_COORDS,
    }


@pytest.mark.parametrize(
    "config",
    [
        {
            CONF_API_KEY: "abcde12345",
            CONF_CITY: "Beijing",
            CONF_STATE: "Beijing",
            CONF_COUNTRY: "China",
        }
    ],
)
async def test_step_geography_by_name(hass, config, setup_airvisual):
    """Test setting up a geography entry by city/state/country."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={"type": INTEGRATION_TYPE_GEOGRAPHY_NAME},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=config
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Cloud API (Beijing, Beijing, China)"
    assert result["data"] == {
        CONF_API_KEY: "abcde12345",
        CONF_CITY: "Beijing",
        CONF_STATE: "Beijing",
        CONF_COUNTRY: "China",
        CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_GEOGRAPHY_NAME,
    }


async def test_step_reauth(hass, config_entry, setup_airvisual):
    """Test that the reauth step works."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_REAUTH}, data=config_entry.data
    )
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    new_api_key = "defgh67890"

    with patch(
        "homeassistant.components.airvisual.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_API_KEY: new_api_key}
        )
        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"

    assert len(hass.config_entries.async_entries()) == 1
    assert hass.config_entries.async_entries()[0].data[CONF_API_KEY] == new_api_key


async def test_step_user(hass):
    """Test the user ("pick the integration type") step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={"type": INTEGRATION_TYPE_GEOGRAPHY_COORDS},
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "geography_by_coords"

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={"type": INTEGRATION_TYPE_GEOGRAPHY_NAME},
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "geography_by_name"
