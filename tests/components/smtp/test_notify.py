"""The tests for the notify smtp platform."""
from os import path
import re

import pytest

from homeassistant import config as hass_config
import homeassistant.components.notify as notify
from homeassistant.components.smtp import DOMAIN
from homeassistant.components.smtp.notify import MailNotificationService
from homeassistant.const import SERVICE_RELOAD
from homeassistant.setup import async_setup_component

from tests.async_mock import patch


class MockSMTP(MailNotificationService):
    """Test SMTP object that doesn't need a working server."""

    def _send_email(self, msg):
        """Just return string for testing."""
        return msg.as_string()


async def test_reload_notify(hass):
    """Verify we can reload the notify service."""

    with patch(
        "homeassistant.components.smtp.notify.MailNotificationService.connection_is_valid"
    ):
        assert await async_setup_component(
            hass,
            notify.DOMAIN,
            {
                notify.DOMAIN: [
                    {
                        "name": DOMAIN,
                        "platform": DOMAIN,
                        "recipient": "test@example.com",
                        "sender": "test@example.com",
                    },
                ]
            },
        )
        await hass.async_block_till_done()

    assert hass.services.has_service(notify.DOMAIN, DOMAIN)

    yaml_path = path.join(
        _get_fixtures_base_path(),
        "fixtures",
        "smtp/configuration.yaml",
    )
    with patch.object(hass_config, "YAML_CONFIG_FILE", yaml_path), patch(
        "homeassistant.components.smtp.notify.MailNotificationService.connection_is_valid"
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await hass.async_block_till_done()

    assert not hass.services.has_service(notify.DOMAIN, DOMAIN)
    assert hass.services.has_service(notify.DOMAIN, "smtp_reloaded")


def _get_fixtures_base_path():
    return path.dirname(path.dirname(path.dirname(__file__)))


@pytest.fixture
def message():
    """Return MockSMTP object with test data."""
    mailer = MockSMTP(
        "localhost",
        25,
        5,
        "test@test.com",
        1,
        "testuser",
        "testpass",
        ["recip1@example.com", "testrecip@test.com"],
        "Home Assistant",
        0,
    )
    yield mailer


html = """
        <!DOCTYPE html>
        <html lang="en" xmlns="http://www.w3.org/1999/xhtml">
            <head><meta charset="UTF-8"></head>
            <body>
              <div>
                <h1>Intruder alert at apartment!!</h1>
              </div>
              <div>
                <img alt="tests/testing_config/media/test.jpg" src="cid:tests/testing_config/media/test.jpg"/>
              </div>
            </body>
        </html>"""

email_data = [
    ("Test msg"),
    ("Test msg", {"images": ["tests/testing_config/media/test.jpg"]}),
    ("Test msg", {"html": html, "images": ["tests/testing_config/media/test.jpg"]}),
    ("Test msg", {"html": html, "images": ["test.jpg"]}),
    ("Test msg", {"html": html, "images": ["tests/testing_config/media/test.pdf"]}),
]


@pytest.mark.parametrize(
    "email_data",
    [email_data[0], email_data[1], email_data[2], email_data[3], email_data[4]],
    ids=[
        "Tests when sending text message",
        "Tests when sending text message and images.",
        "Tests when sending text message, HTML Template and images.",
        "Tests when image does not exist at mentioned location.",
        "Tests when image type cannot be detected or is of wrong type.",
    ],
)
def test_send_message(email_data, hass, message):
    """Verify if we can send messages of all types correctly."""
    sample_email = "<mock@mock>"
    with patch("email.utils.make_msgid", return_value=sample_email):
        if isinstance(email_data, tuple):
            result = message.send_message(email_data[0], data=email_data[1])
        elif isinstance(email_data, str):
            result = message.send_message(email_data)

        expected = (
            '^Content-Type: text/plain; charset="us-ascii"\n'
            "MIME-Version: 1.0\n"
            "Content-Transfer-Encoding: 7bit\n"
            "Subject: Home Assistant\n"
            "To: recip1@example.com,testrecip@test.com\n"
            "From: Home Assistant <test@test.com>\n"
            "X-Mailer: Home Assistant\n"
            "Date: [^\n]+\n"
            "Message-Id: <[^@]+@[^>]+>\n"
            "\n"
            "Test msg$"
        )
        if isinstance(email_data, str):
            assert re.search(expected, result)
        elif isinstance(email_data, tuple):
            assert "Content-Type: multipart/related" in result
