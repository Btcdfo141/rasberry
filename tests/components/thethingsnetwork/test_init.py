"""Define tests for the The Things Network init."""

import pytest
from ttn_client import TTNAuthError

from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.setup import async_setup_component

from .conftest import (
    APP_ID,
    CONFIG_ENTRY,
    DATA_UPDATE,
    DEVICE_FIELD,
    DEVICE_FIELD_2,
    DEVICE_ID,
    DEVICE_ID_2,
    DOMAIN,
)


async def test_normal(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_TTNClient,
) -> None:
    """Test a working configurations."""
    CONFIG_ENTRY.add_to_hass(hass)
    assert await hass.config_entries.async_setup(CONFIG_ENTRY.entry_id)

    await hass.async_block_till_done()

    # Check devices
    assert (
        device_registry.async_get_device(
            identifiers={(DOMAIN, f"{APP_ID}_{DEVICE_ID}")}
        ).name
        == DEVICE_ID
    )

    # Check entities
    assert entity_registry.async_get(f"sensor.{DEVICE_ID}_{DEVICE_FIELD}")

    assert not entity_registry.async_get(f"sensor.{DEVICE_ID_2}_{DEVICE_FIELD}")
    push_callback = mock_TTNClient.call_args.kwargs["push_callback"]
    await push_callback(DATA_UPDATE)
    assert entity_registry.async_get(f"sensor.{DEVICE_ID_2}_{DEVICE_FIELD_2}")


@pytest.mark.parametrize(("exception_class"), [TTNAuthError, Exception])
async def test_client_exceptions(
    hass: HomeAssistant, mock_TTNClient, exception_class
) -> None:
    """Test TTN Exceptions."""

    mock_TTNClient.return_value.fetch_data.side_effect = exception_class
    CONFIG_ENTRY.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(CONFIG_ENTRY.entry_id)


async def test_error_configuration(
    hass: HomeAssistant,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test issue is logged when deprecated configuration is used."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})
    await hass.async_block_till_done()
    assert issue_registry.async_get_issue(DOMAIN, "manual_migration")
