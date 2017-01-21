"""The tests for Home Assistant frontend."""
# pylint: disable=protected-access
import re
import unittest
from unittest.mock import Mock, patch
import requests

import homeassistant.bootstrap as bootstrap
from homeassistant.components import http
from homeassistant.components.frontend import register_custom_ui
from homeassistant.const import HTTP_HEADER_HA_AUTH

from tests.common import get_test_instance_port, get_test_home_assistant

API_PASSWORD = "test1234"
SERVER_PORT = get_test_instance_port()
HTTP_BASE_URL = "http://127.0.0.1:{}".format(SERVER_PORT)
HA_HEADERS = {HTTP_HEADER_HA_AUTH: API_PASSWORD}

# pylint: disable=invalid-name
hass = None


def _url(path=""):
    """Helper method to generate URLs."""
    return HTTP_BASE_URL + path


# pylint: disable=invalid-name
def setUpModule():
    """Initialize a Home Assistant server."""
    global hass

    hass = get_test_home_assistant()

    assert bootstrap.setup_component(
        hass, http.DOMAIN,
        {http.DOMAIN: {http.CONF_API_PASSWORD: API_PASSWORD,
                       http.CONF_SERVER_PORT: SERVER_PORT}})

    assert bootstrap.setup_component(hass, 'frontend')

    hass.start()


# pylint: disable=invalid-name
def tearDownModule():
    """Stop everything that was started."""
    hass.stop()


class TestFrontend(unittest.TestCase):
    """Test the frontend."""

    def tearDown(self):
        """Stop everything that was started."""
        hass.block_till_done()

    def test_frontend_and_static(self):
        """Test if we can get the frontend."""
        req = requests.get(_url(""))
        self.assertEqual(200, req.status_code)

        # Test we can retrieve frontend.js
        frontendjs = re.search(
            r'(?P<app>\/static\/frontend-[A-Za-z0-9]{32}.html)',
            req.text)

        self.assertIsNotNone(frontendjs)
        req = requests.get(_url(frontendjs.groups(0)[0]))
        self.assertEqual(200, req.status_code)

    def test_404(self):
        """Test for HTTP 404 error."""
        self.assertEqual(404, requests.get(_url("/not-existing")).status_code)

    def test_we_cannot_POST_to_root(self):
        """Test that POST is not allow to root."""
        self.assertEqual(405, requests.post(_url("")).status_code)

    def test_states_routes(self):
        """All served by index."""
        req = requests.get(_url("/states"))
        self.assertEqual(200, req.status_code)

        req = requests.get(_url("/states/group.non_existing"))
        self.assertEqual(404, req.status_code)

        hass.states.set('group.existing', 'on', {'view': True})
        req = requests.get(_url("/states/group.existing"))
        self.assertEqual(200, req.status_code)

    def test_api_bootstrap_require_auth(self):
        """Test that /api/bootstrap path requires auth."""
        req = requests.get(_url("/api/bootstrap"))
        self.assertEqual(401, req.status_code)

    def test_api_bootstrap_has_cutom_ui_field(self):
        """Test /api/bootstrap path."""
        req = requests.get(_url("/api/bootstrap"), headers=HA_HEADERS)
        self.assertEqual(200, req.status_code)
        self.assertIn('custom_ui', req.json())

    def test_register_custom_ui(self):
        """Test register_custom_ui."""
        with patch('os.path.isfile', Mock(return_value=True)):
            register_custom_ui(hass, 'custom_name', 'fake.path')
        req = requests.get(_url("/api/bootstrap"), headers=HA_HEADERS)
        self.assertEqual(200, req.status_code)
        custom_uis = req.json().get('custom_ui')
        self.assertIn('custom_name', custom_uis)
        custom_ui = custom_uis.get('custom_name')
        self.assertEqual('custom_name', custom_ui.get('component_name'))
        self.assertEqual(
            '/frontend/custom_ui/custom_name.html', custom_ui.get('url'))

    def test_register_custom_ui_url_path(self):
        """Test register_custom_ui on specific url path."""
        with patch('os.path.isfile', Mock(return_value=True)):
            register_custom_ui(
                hass, 'custom_name', 'fake.path', url_path='/some.url')
        req = requests.get(_url("/api/bootstrap"), headers=HA_HEADERS)
        self.assertEqual(200, req.status_code)
        custom_uis = req.json().get('custom_ui')
        self.assertIn('custom_name', custom_uis)
        custom_ui = custom_uis.get('custom_name')
        self.assertEqual('/some.url', custom_ui.get('url'))

    def test_register_custom_ui_config(self):
        """Test register_custom_ui with config."""
        with patch('os.path.isfile', Mock(return_value=True)):
            register_custom_ui(
                hass, 'custom_name', 'fake.path', config={'key': 'value'})
        req = requests.get(_url("/api/bootstrap"), headers=HA_HEADERS)
        self.assertEqual(200, req.status_code)
        custom_uis = req.json().get('custom_ui')
        self.assertIn('custom_name', custom_uis)
        custom_ui = custom_uis.get('custom_name')
        self.assertEqual({'key': 'value'}, custom_ui.get('config'))
