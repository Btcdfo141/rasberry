"""Support for Sinch notifications."""
import logging

import voluptuous as vol
from clx.xms.api import MtBatchTextSmsResult
from clx.xms.client import Client
from clx.xms.exceptions import (
    ErrorResponseException,
    UnexpectedResponseException,
    UnauthorizedException,
    NotFoundException,
)

import homeassistant.helpers.config_validation as cv
from homeassistant.components.notify import (
    ATTR_MESSAGE,
    ATTR_DATA,
    ATTR_TARGET,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)
from homeassistant.const import CONF_API_KEY, CONF_SENDER

DOMAIN = "sinch"

CONF_SERVICE_PLAN_ID = "service_plan_id"
CONF_DEFAULT_RECIPIENTS = "default_recipients"

ATTR_SENDER = CONF_SENDER

DEFAULT_SENDER = "Home Assistant"

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_SERVICE_PLAN_ID): cv.string,
        vol.Optional(CONF_SENDER, default=DEFAULT_SENDER): cv.string,
        vol.Optional(CONF_DEFAULT_RECIPIENTS, default=[]): vol.All(
            cv.ensure_list, [cv.string]
        ),
    }
)


def get_service(hass, config, discovery_info=None):
    """Get the Sinch notification service."""
    return SinchNotificationService(config)


class SinchNotificationService(BaseNotificationService):
    """Send Notifications to Sinch SMS recipients."""

    def __init__(self, config):
        """Initialize the service."""
        self.default_recipients = config[CONF_DEFAULT_RECIPIENTS]
        self.sender = config[CONF_SENDER]
        self.client = Client(config[CONF_SERVICE_PLAN_ID], config[CONF_API_KEY])

    def send_message(self, message="", **kwargs):
        """Send a message to a user."""
        targets = kwargs.get(ATTR_TARGET, self.default_recipients)
        data = kwargs.get(ATTR_DATA, {})

        clx_args = {ATTR_MESSAGE: message, ATTR_SENDER: self.sender}

        if ATTR_SENDER in data:
            clx_args[ATTR_SENDER] = data[ATTR_SENDER]

        if not targets:
            _LOGGER.error("At least 1 target is required")
            return

        try:
            for target in targets:
                result: MtBatchTextSmsResult = self.client.create_text_message(
                    clx_args[ATTR_SENDER], target, clx_args[ATTR_MESSAGE]
                )
                batch_id = result.batch_id
                _LOGGER.debug(
                    'Successfully sent SMS to "%s" (batch_id: %s)', target, batch_id
                )
        except ErrorResponseException as ex:
            _LOGGER.error(
                "Caught ErrorResponseException. Response code: %d (%s)", ex.error_code, ex
            )
        except NotFoundException as ex:
            _LOGGER.error("Caught NotFoundException (request URL: %s)", ex.url)
        except UnauthorizedException as ex:
            _LOGGER.error(
                "Caught UnauthorizedException (service plan: %s)", ex.service_plan_id
            )
        except UnexpectedResponseException as ex:
            _LOGGER.error("Caught UnexpectedResponseException: %s", ex)
        except Exception as ex:
            _LOGGER.error("Unexpected error while creating batch: %s", ex)
