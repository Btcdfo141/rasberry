"""Manage Viam client connection."""

import base64
from typing import Any

from PIL import Image
from viam.app.app_client import RobotPart
from viam.app.viam_client import ViamClient
from viam.robot.client import RobotClient
from viam.rpc.dial import Credentials, DialOptions
from viam.services.vision.client import RawImage

from homeassistant.components import camera
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from .const import (
    CONF_CREDENTIAL_TYPE,
    CONF_ROBOT_ID,
    CONF_SECRET,
    CRED_TYPE_API_KEY,
    CRED_TYPE_LOCATION_SECRET,
    DOMAIN,
)


def _fetch_image(filepath: str | None):
    if filepath is None:
        return None
    return Image.open(filepath)


class ViamManager:
    """Manage Viam client and entry data."""

    def __init__(
        self,
        hass: HomeAssistant,
        viam: ViamClient,
        entry_id: str,
        data: dict[str, Any],
    ) -> None:
        """Store initialized client and user input data."""
        self.hass = hass
        self.viam = viam
        self.data = data
        self.entry_id = entry_id

    def unload(self) -> None:
        """Clean up any open clients."""
        self.viam.close()

    def encode_image(self, image: Image.Image | RawImage):
        """Create base64-encoded Image string."""
        image_bytes = b""
        if isinstance(image, Image.Image):
            image_bytes = image.tobytes()
        if isinstance(image, RawImage):
            image_bytes = image.data

        image_string = base64.b64encode(image_bytes).decode()
        return f"data:image/jpeg;base64,{image_string}"

    async def get_image(self, filepath: str | None, camera_entity: str | None):
        """Retrieve image type from camera entity or file system."""
        if filepath is not None:
            return await self.hass.async_add_executor_job(_fetch_image, filepath)
        if camera_entity is not None:
            image = await camera.async_get_image(self.hass, camera_entity)
            return RawImage(image.content, image.content_type)

        return None

    async def get_robot_client(
        self, robot_secret: str | None, robot_address: str | None
    ) -> RobotClient:
        """Check initialized data to create robot client."""
        address = self.data.get(CONF_ADDRESS)
        payload = self.data.get(CONF_SECRET)
        if self.data[CONF_CREDENTIAL_TYPE] == CRED_TYPE_API_KEY:
            if robot_secret is None or robot_address is None:
                raise ServiceValidationError(
                    "The robot location and secret are required for this connection type.",
                    translation_domain=DOMAIN,
                    translation_key="robot_credentials_required",
                )
            address = robot_address
            payload = robot_secret

        if address is None or payload is None:
            raise ServiceValidationError(
                "The necessary credentials for the RobotClient could not be found.",
                translation_domain=DOMAIN,
                translation_key="robot_credentials_not_found",
            )

        credentials = Credentials(type=CRED_TYPE_LOCATION_SECRET, payload=payload)
        robot_options = RobotClient.Options(
            refresh_interval=0, dial_options=DialOptions(credentials=credentials)
        )
        return await RobotClient.at_address(address, robot_options)

    async def get_robot_parts(self) -> list[RobotPart]:
        """Retrieve list of robot parts."""
        return await self.viam.app_client.get_robot_parts(
            robot_id=self.data[CONF_ROBOT_ID]
        )
