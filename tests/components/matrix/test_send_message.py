"""Test the send_message service."""

from homeassistant.components.matrix import (
    ATTR_IMAGES,
    DOMAIN as MATRIX_DOMAIN,
    MatrixBot,
)
from homeassistant.components.matrix.const import SERVICE_SEND_MESSAGE
from homeassistant.components.notify import ATTR_DATA, ATTR_MESSAGE, ATTR_TARGET
from homeassistant.core import HomeAssistant

from tests.components.matrix.conftest import TEST_BAD_ROOM, TEST_JOINABLE_ROOMS


async def test_send_message(
    hass: HomeAssistant, matrix_bot: MatrixBot, image_path, matrix_events, caplog
):
    """Test the send_message service."""
    assert len(matrix_events) == 0
    await matrix_bot._login()

    # Send a message without an attached image.
    data = {ATTR_MESSAGE: "Test message", ATTR_TARGET: TEST_JOINABLE_ROOMS}
    await hass.services.async_call(
        MATRIX_DOMAIN, SERVICE_SEND_MESSAGE, data, blocking=True
    )
    await hass.async_block_till_done()

    for room_id in TEST_JOINABLE_ROOMS:
        assert f"Message delivered to room '{room_id}'" in caplog.messages

    # Send a message with an attached image.
    data[ATTR_DATA] = {ATTR_IMAGES: [image_path.name]}
    await hass.services.async_call(
        MATRIX_DOMAIN, SERVICE_SEND_MESSAGE, data, blocking=True
    )
    await hass.async_block_till_done()

    for room_id in TEST_JOINABLE_ROOMS:
        assert f"Image '{image_path.name}' sent to room '{room_id}'" in caplog.messages


async def test_unsendable_message(
    hass: HomeAssistant, matrix_bot: MatrixBot, matrix_events, caplog
):
    """Test the send_message service with an invalid room."""
    assert len(matrix_events) == 0
    await matrix_bot._login()

    data = {ATTR_MESSAGE: "Test message", ATTR_TARGET: TEST_BAD_ROOM}

    await hass.services.async_call(
        MATRIX_DOMAIN, SERVICE_SEND_MESSAGE, data, blocking=True
    )
    await hass.async_block_till_done()

    assert (
        f"Unable to deliver message to room '{TEST_BAD_ROOM}': ErrorResponse: Cannot send a message in this room."
        in caplog.messages
    )
