"""Test Roborock Number platform."""
from unittest.mock import patch

import pytest
from roborock.exceptions import RoborockException

from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("entity_id", "value"),
    [
        ("number.roborock_s7_maxv_volume", 3.0),
    ],
)
async def test_update_success(
    hass: HomeAssistant,
    bypass_api_fixture,
    setup_entry: MockConfigEntry,
    entity_id: str,
    value: float,
) -> None:
    """Test allowed changing values for number entities."""
    with patch(
        "homeassistant.components.roborock.coordinator.RoborockLocalClient.send_message"
    ) as mock_send_message:
        await hass.services.async_call(
            "number",
            SERVICE_SET_VALUE,
            service_data={ATTR_VALUE: value},
            blocking=True,
            target={"entity_id": entity_id},
        )
    assert mock_send_message.assert_called_once


async def test_update_failure(
    hass: HomeAssistant,
    bypass_api_fixture,
    setup_entry: MockConfigEntry,
) -> None:
    """Test that changing a value will raise a homeassistanterror when it fails."""
    with patch(
        "homeassistant.components.roborock.coordinator.RoborockLocalClient.send_message",
        side_effect=RoborockException(),
    ), pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "number",
            SERVICE_SET_VALUE,
            service_data={ATTR_VALUE: 3.3},
            blocking=True,
            target={"entity_id": "number.roborock_s7_maxv_volume"},
        )
