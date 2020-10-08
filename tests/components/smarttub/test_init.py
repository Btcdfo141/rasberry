"""Test smarttub setup process."""

import pytest

from homeassistant.components import smarttub
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.setup import async_setup_component

from tests.async_mock import patch


@pytest.fixture
def mock_controller(coordinator):
    """Mock the controller."""
    with patch.object(
        smarttub, "SmartTubController", autospec=True
    ) as controller_class_mock:
        controller_mock = controller_class_mock.return_value
        controller_mock.coordinator = coordinator
        yield controller_mock


async def test_setup_with_no_config(hass, mock_controller):
    """Test that we do not discover anything."""
    assert await async_setup_component(hass, smarttub.DOMAIN, {}) is True

    # No flows started
    assert len(hass.config_entries.flow.async_progress()) == 0

    mock_controller.async_setup_entry.assert_not_called()


async def test_setup_entry_not_ready(hass, mock_controller, config_entry):
    """Test setup when the entry is not ready."""
    mock_controller.coordinator.last_update_success = False
    assert await async_setup_component(hass, smarttub.DOMAIN, {}) is True

    with pytest.raises(ConfigEntryNotReady):
        await smarttub.async_setup_entry(hass, config_entry)


async def test_config_passed_to_config_entry(
    hass, mock_controller, config_entry, config_data
):
    """Test that configured options are loaded via config entry."""
    config_entry.add_to_hass(hass)
    mock_controller.async_setup_entry.return_value = True
    ret = await async_setup_component(hass, smarttub.DOMAIN, config_data)
    assert ret is True

    mock_controller.async_setup_entry.assert_called_once_with(config_entry)


async def test_unload_entry(hass, mock_controller, config_entry):
    """Test being able to unload an entry."""
    config_entry.add_to_hass(hass)

    assert await async_setup_component(hass, smarttub.DOMAIN, {}) is True
    mock_controller.async_setup_entry.assert_called()

    assert await smarttub.async_unload_entry(hass, config_entry)
    mock_controller.async_unload_entry.assert_called()
