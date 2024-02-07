"""Services for Viam integration."""
from __future__ import annotations

from datetime import datetime
from functools import partial

from viam.app.app_client import RobotPart
from viam.services.vision import VisionClient
import voluptuous as vol

from homeassistant.components import camera
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    SERVICE_CAMERA,
    SERVICE_CLASSIFIER_NAME,
    SERVICE_COMPONENT_NAME,
    SERVICE_COMPONENT_TYPE,
    SERVICE_CONFIDENCE,
    SERVICE_COUNT,
    SERVICE_DETECTOR_NAME,
    SERVICE_FILE_NAME,
    SERVICE_FILEPATH,
    SERVICE_ROBOT_ADDRESS,
    SERVICE_ROBOT_SECRET,
    SERVICE_VALUES,
)
from .manager import ViamManager

ATTR_CONFIG_ENTRY = "config_entry"

DATA_CAPTURE_SERVICE_NAME = "capture_data"
CAPTURE_IMAGE_SERVICE_NAME = "capture_image"
CLASSIFICATION_SERVICE_NAME = "get_classifications"
DETECTIONS_SERVICE_NAME = "get_detections"

ENTRY_SERVICE_SCHEMA = {
    vol.Required(ATTR_CONFIG_ENTRY): selector.ConfigEntrySelector(
        {
            "integration": DOMAIN,
        }
    ),
}
DATA_CAPTURE_SERVICE_SCHEMA = vol.Schema(
    {
        **ENTRY_SERVICE_SCHEMA,
        vol.Required(SERVICE_VALUES): vol.All(dict),
        vol.Required(SERVICE_COMPONENT_NAME): vol.All(str),
        vol.Required(SERVICE_COMPONENT_TYPE, default="sensor"): vol.All(str),
    }
)

IMAGE_SERVICE_FIELDS = {
    vol.Optional(SERVICE_FILEPATH): vol.All(str, vol.IsFile),
    vol.Optional(SERVICE_CAMERA): vol.All(str),
}
VISION_SERVICE_FIELDS = {
    vol.Optional(SERVICE_CONFIDENCE, default="0.6"): vol.All(
        str, vol.Coerce(float), vol.Range(min=0, max=1)
    ),
    vol.Optional(SERVICE_ROBOT_ADDRESS): vol.All(str),
    vol.Optional(SERVICE_ROBOT_SECRET): vol.All(str),
}

CAPTURE_IMAGE_SERVICE_SCHEMA = vol.Schema(
    {
        **ENTRY_SERVICE_SCHEMA,
        **IMAGE_SERVICE_FIELDS,
        vol.Optional(SERVICE_FILE_NAME, default="camera"): vol.All(str),
        vol.Optional(SERVICE_COMPONENT_NAME): vol.All(str),
    }
)

CLASSIFICATION_SERVICE_SCHEMA = vol.Schema(
    {
        **ENTRY_SERVICE_SCHEMA,
        **IMAGE_SERVICE_FIELDS,
        **VISION_SERVICE_FIELDS,
        vol.Required(SERVICE_CLASSIFIER_NAME): vol.All(str),
        vol.Optional(SERVICE_COUNT, default="2"): vol.All(str, vol.Coerce(int)),
    }
)

DETECTIONS_SERVICE_SCHEMA = vol.Schema(
    {
        **ENTRY_SERVICE_SCHEMA,
        **IMAGE_SERVICE_FIELDS,
        **VISION_SERVICE_FIELDS,
        vol.Required(SERVICE_DETECTOR_NAME): vol.All(str),
    }
)


def __get_manager(hass: HomeAssistant, call: ServiceCall) -> ViamManager:
    entry_id: str = call.data[ATTR_CONFIG_ENTRY]
    entry: ConfigEntry | None = hass.config_entries.async_get_entry(entry_id)

    if not entry:
        raise ServiceValidationError(
            f"Invalid config entry: {entry_id}",
            translation_domain=DOMAIN,
            translation_key="invalid_config_entry",
            translation_placeholders={
                "config_entry": entry_id,
            },
        )
    if entry.state != ConfigEntryState.LOADED:
        raise ServiceValidationError(
            f"{entry.title} is not loaded",
            translation_domain=DOMAIN,
            translation_key="unloaded_config_entry",
            translation_placeholders={
                "config_entry": entry.title,
            },
        )

    manager: ViamManager = hass.data[DOMAIN][entry_id]
    return manager


async def __capture_data(call: ServiceCall, *, hass: HomeAssistant) -> None:
    """Accept input from service call to send to Viam."""
    manager: ViamManager = __get_manager(hass, call)
    parts: list[RobotPart] = await manager.get_robot_parts()
    values = [call.data.get(SERVICE_VALUES)]
    component_type = call.data.get(SERVICE_COMPONENT_TYPE, "sensor")
    component_name = call.data.get(SERVICE_COMPONENT_NAME)

    await manager.viam.data_client.tabular_data_capture_upload(
        tabular_data=values,
        part_id=parts.pop().id,
        component_type=component_type,
        component_name=component_name,
        method_name="capture_data",
        data_request_times=[(datetime.now(), datetime.now())],
    )


async def __capture_image(call: ServiceCall, *, hass: HomeAssistant) -> None:
    """Accept input from service call to send to Viam."""
    manager: ViamManager = __get_manager(hass, call)
    parts: list[RobotPart] = await manager.get_robot_parts()
    filepath = call.data.get(SERVICE_FILEPATH)
    camera_entity = call.data.get(SERVICE_CAMERA)
    component_name = call.data.get(SERVICE_COMPONENT_NAME)
    file_name = call.data.get(SERVICE_FILE_NAME, "camera")

    if filepath is not None:
        await manager.viam.data_client.file_upload_from_path(
            filepath=filepath,
            part_id=parts.pop().id,
            component_name=component_name,
        )
    if camera_entity is not None:
        image = await camera.async_get_image(hass, camera_entity)
        await manager.viam.data_client.file_upload(
            part_id=parts.pop().id,
            component_name=component_name,
            file_name=file_name,
            file_extension=".jpeg",
            data=image.content,
        )


async def __get_classifications(
    call: ServiceCall, *, hass: HomeAssistant
) -> ServiceResponse:
    """Accept input configuration to request classifications."""
    manager: ViamManager = __get_manager(hass, call)
    filepath = call.data.get(SERVICE_FILEPATH)
    camera_entity = call.data.get(SERVICE_CAMERA)
    classifier_name = call.data.get(SERVICE_CLASSIFIER_NAME, "")
    count = int(call.data.get(SERVICE_COUNT, 2))
    confidence_threshold = float(call.data.get(SERVICE_CONFIDENCE, 0.6))

    async with await manager.get_robot_client(
        call.data.get(SERVICE_ROBOT_SECRET), call.data.get(SERVICE_ROBOT_ADDRESS)
    ) as robot:
        classifier = VisionClient.from_robot(robot, classifier_name)
        image = await manager.get_image(filepath, camera_entity)

    if image is None:
        return {
            "classifications": [],
            "img_src": filepath or None,
        }

    img_src = filepath or manager.encode_image(image)
    classifications = await classifier.get_classifications(image, count)

    return {
        "classifications": [
            {"name": c.class_name, "confidence": c.confidence}
            for c in classifications
            if c.confidence >= confidence_threshold
        ],
        "img_src": img_src,
    }


async def __get_detections(
    call: ServiceCall, *, hass: HomeAssistant
) -> ServiceResponse:
    """Accept input configuration to request detections."""
    manager: ViamManager = __get_manager(hass, call)
    filepath = call.data.get(SERVICE_FILEPATH)
    camera_entity = call.data.get(SERVICE_CAMERA)
    detector_name = call.data.get(SERVICE_DETECTOR_NAME, "")
    confidence_threshold = float(call.data.get(SERVICE_CONFIDENCE, 0.6))

    async with await manager.get_robot_client(
        call.data.get(SERVICE_ROBOT_SECRET), call.data.get(SERVICE_ROBOT_ADDRESS)
    ) as robot:
        detector = VisionClient.from_robot(robot, detector_name)
        image = await manager.get_image(filepath, camera_entity)

    if image is None:
        return {
            "detections": [],
            "img_src": filepath or None,
        }

    img_src = filepath or manager.encode_image(image)
    detections = await detector.get_detections(image)

    return {
        "detections": [
            {
                "name": c.class_name,
                "confidence": c.confidence,
                "x_min": c.x_min,
                "y_min": c.y_min,
                "x_max": c.x_max,
                "y_max": c.y_max,
            }
            for c in detections
            if c.confidence >= confidence_threshold
        ],
        "img_src": img_src,
    }


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Viam integration."""

    hass.services.async_register(
        DOMAIN,
        DATA_CAPTURE_SERVICE_NAME,
        partial(__capture_data, hass=hass),
        DATA_CAPTURE_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        CAPTURE_IMAGE_SERVICE_NAME,
        partial(__capture_image, hass=hass),
        CAPTURE_IMAGE_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        CLASSIFICATION_SERVICE_NAME,
        partial(__get_classifications, hass=hass),
        CLASSIFICATION_SERVICE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        DETECTIONS_SERVICE_NAME,
        partial(__get_detections, hass=hass),
        DETECTIONS_SERVICE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
