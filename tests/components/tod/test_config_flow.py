"""Test the Times of the Day config flow."""
from unittest.mock import patch

from freezegun import freeze_time
import pytest

from homeassistant import config_entries
from homeassistant.components.tod.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM

from tests.common import MockConfigEntry


@pytest.mark.parametrize("platform", ("sensor",))
async def test_config_flow(hass: HomeAssistant, platform) -> None:
    """Test the config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.tod.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "after": "absolute_time",
                "after_offset": {"minutes": 10},
                "after_time": "10:00",
                "before": "sunset",
                "before_offset": {"minutes": -10},
                "name": "My tod",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "My tod"
    assert result["data"] == {}
    assert result["options"] == {
        "after": "absolute_time",
        "after_offset": {"minutes": 10},
        "after_time": "10:00",
        "before": "sunset",
        "before_offset": {"minutes": -10},
        "name": "My tod",
    }
    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options == {
        "after": "absolute_time",
        "after_offset": {"minutes": 10},
        "after_time": "10:00",
        "before": "sunset",
        "before_offset": {"minutes": -10},
        "name": "My tod",
    }
    assert config_entry.title == "My tod"


def get_suggested(schema, key):
    """Get suggested value for key in voluptuous schema."""
    for k in schema.keys():
        if k == key:
            if k.description is None or "suggested_value" not in k.description:
                return None
            return k.description["suggested_value"]
    # Wanted key absent from schema
    raise Exception


@freeze_time("2022-03-16 17:37:00", tz_offset=-7)
async def test_options(hass: HomeAssistant) -> None:
    """Test reconfiguring."""
    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "after": "absolute_time",
            "after_offset": {"minutes": 10.0},
            "after_time": "10:00:00",
            "before": "sunset",
            "before_offset": {"minutes": -10.0},
            "name": "My tod",
        },
        title="My tod",
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "init"
    schema = result["data_schema"].schema
    assert get_suggested(schema, "after") == "absolute_time"
    assert get_suggested(schema, "after_offset") == {"minutes": 10.0}
    assert get_suggested(schema, "after_time") == "10:00:00"
    assert get_suggested(schema, "before") == "sunset"
    assert get_suggested(schema, "before_offset") == {"minutes": -10.0}
    assert get_suggested(schema, "before_time") is None

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "after": "sunset",
            "after_offset": {"seconds": 0.0},
            "before": "absolute_time",
            "before_offset": {"seconds": 0.0},
            "before_time": "23:00",
        },
    )
    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["data"] == {
        "after": "sunset",
        "after_offset": {"seconds": 0.0},
        "after_time": "10:00:00",
        "before": "absolute_time",
        "before_offset": {"seconds": 0.0},
        "before_time": "23:00",
        "name": "My tod",
    }
    assert config_entry.data == {}
    assert config_entry.options == {
        "after": "sunset",
        "after_offset": {"seconds": 0.0},
        "after_time": "10:00:00",
        "before": "absolute_time",
        "before_offset": {"seconds": 0.0},
        "before_time": "23:00",
        "name": "My tod",
    }
    assert config_entry.title == "My tod"

    # Check config entry is reloaded with new options
    await hass.async_block_till_done()

    # Check the entity was updated, no new entity was created
    assert len(hass.states.async_all()) == 1

    # Check the state of the entity has changed as expected
    state = hass.states.get("binary_sensor.my_tod")
    assert state.state == "off"
    assert state.attributes["after"] == "2022-03-16T18:57:27.925823-07:00"
    assert state.attributes["before"] == "2022-03-17T16:00:00-07:00"
