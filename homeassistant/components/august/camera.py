"""Support for August doorbell camera."""

from august.activity import ActivityType
from august.util import update_doorbell_image_from_activity

from homeassistant.components.camera import Camera
from homeassistant.core import callback

from .const import DATA_AUGUST, DEFAULT_NAME, DEFAULT_TIMEOUT, DOMAIN
from .entity import AugustEntityMixin


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up August cameras."""
    data = hass.data[DOMAIN][config_entry.entry_id][DATA_AUGUST]
    devices = []

    for doorbell in data.doorbells:
        devices.append(AugustCamera(data, doorbell, DEFAULT_TIMEOUT))

    async_add_entities(devices, True)


class AugustCamera(AugustEntityMixin, Camera):
    """An implementation of a August security camera."""

    def __init__(self, data, device, timeout):
        """Initialize a August security camera."""
        super().__init__(data, device)
        self._data = data
        self._device = device
        self._timeout = timeout
        self._image_url = None
        self._image_content = None

    @property
    def name(self):
        """Return the name of this device."""
        return f"{self._device.device_name} Camera"

    @property
    def is_recording(self):
        """Return true if the device is recording."""
        return self._device.has_subscription

    @property
    def motion_detection_enabled(self):
        """Return the camera motion detection status."""
        return True

    @property
    def brand(self):
        """Return the camera brand."""
        return DEFAULT_NAME

    @property
    def model(self):
        """Return the camera model."""
        return self._detail.model

    @callback
    def _update_from_data(self):
        """Get the latest state of the sensor."""
        doorbell_activity = self._data.activity_stream.get_latest_device_activity(
            self._device_id, [ActivityType.DOORBELL_MOTION]
        )

        if doorbell_activity is not None:
            update_doorbell_image_from_activity(self._detail, doorbell_activity)

    async def async_camera_image(self):
        """Return bytes of camera image."""
        self._update_from_data()

        if self._image_url is not self._detail.image_url:
            self._image_url = self._detail.image_url
            self._image_content = await self.hass.async_add_executor_job(
                self._camera_image
            )
        return self._image_content

    def _camera_image(self):
        """Return bytes of camera image."""
        return self._detail.get_doorbell_image(timeout=self._timeout)

    @property
    def unique_id(self) -> str:
        """Get the unique id of the camera."""
        return f"{self._device_id:s}_camera"
