"""Unify Circuit platform for notify component."""
import logging

from circuit_webhook import Circuit

from homeassistant.components.notify import ATTR_TARGET, BaseNotificationService
from homeassistant.const import CONF_URL

_LOGGER = logging.getLogger(__name__)


def get_service(hass, config, discovery_info=None):
    """Get the Unify Circuit notification service."""
    if discovery_info is None:
        return

    return CircuitNotificationService(discovery_info)


class CircuitNotificationService(BaseNotificationService):
    """Implement the notification service for Unify Circuit."""

    def __init__(self, webhook_url):
        """Initialize the service."""
        self.webhook_url = webhook_url[CONF_URL]

    def send_message(self, message=None, **kwargs):
        """Send a message to the webhook."""

        webhook_url = self.webhook_url
        target = kwargs.get(ATTR_TARGET, webhook_url)

        if target and message:
            try:
                circuit_message = Circuit(url=target)
                circuit_message.post(text=message)
            except RuntimeError as err:
                _LOGGER.error("Could not send notification. Error: %s", err)
