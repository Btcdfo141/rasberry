"""The tests for the facebox component."""
from unittest.mock import patch

import pytest
import requests
import requests_mock
from unittest import mock

from homeassistant.core import callback
from homeassistant.const import (
    ATTR_ENTITY_ID, ATTR_NAME, CONF_FRIENDLY_NAME,
    CONF_IP_ADDRESS, CONF_PORT, STATE_UNKNOWN)
from homeassistant.setup import async_setup_component
import homeassistant.components.image_processing as ip
import homeassistant.components.image_processing.facebox as fb

MOCK_IP = '192.168.0.1'
MOCK_PORT = '8080'

# Mock data returned by the facebox API.
MOCK_ERROR = "No face found"
MOCK_FACE = {'confidence': 0.5812028911604818,
             'id': 'john.jpg',
             'matched': True,
             'name': 'John Lennon',
             'rect': {'height': 75, 'left': 63, 'top': 262, 'width': 74}
             }

MOCK_FILE_PATH = '/images/mock.jpg'

MOCK_JSON = {"facesCount": 1,
             "success": True,
             "faces": [MOCK_FACE]
             }

MOCK_NAME = 'mock_name'

# Faces data after parsing.
PARSED_FACES = [{ATTR_NAME: 'John Lennon',
                 fb.ATTR_IMAGE_ID: 'john.jpg',
                 fb.ATTR_CONFIDENCE: 58.12,
                 fb.ATTR_MATCHED: True,
                 fb.ATTR_BOUNDING_BOX: {
                     'height': 75,
                     'left': 63,
                     'top': 262,
                     'width': 74},
                 }]

MATCHED_FACES = {'John Lennon': 58.12}

VALID_ENTITY_ID = 'image_processing.facebox_demo_camera'
VALID_CONFIG = {
    ip.DOMAIN: {
        'platform': 'facebox',
        CONF_IP_ADDRESS: MOCK_IP,
        CONF_PORT: MOCK_PORT,
        ip.CONF_SOURCE: {
            ip.CONF_ENTITY_ID: 'camera.demo_camera'}
        },
    'camera': {
        'platform': 'demo'
        }
    }


def test_encode_image():
    """Test that binary data is encoded correctly."""
    assert fb.encode_image(b'test') == 'dGVzdA=='


def test_get_matched_faces():
    """Test that matched_faces are parsed correctly."""
    assert fb.get_matched_faces(PARSED_FACES) == MATCHED_FACES


def test_parse_faces():
    """Test parsing of raw face data, and generation of matched_faces."""
    assert fb.parse_faces(MOCK_JSON['faces']) == PARSED_FACES


def test_valid_file_path():
    """Test that an invalid file_path is caught."""
    with mock.patch('os.access', mock.Mock(return_value=False)):
        assert not fb.valid_file_path('test_path')


def test_valid_image():
    """Test for valid images."""
    assert fb.valid_image('test.jpg')
    assert not fb.valid_image('test.foo')


@pytest.fixture
def mock_image():
    """Return a mock camera image."""
    with patch('homeassistant.components.camera.demo.DemoCamera.camera_image',
               return_value=b'Test') as image:
        yield image


async def test_setup_platform(hass):
    """Setup platform with one entity."""
    await async_setup_component(hass, ip.DOMAIN, VALID_CONFIG)
    assert hass.states.get(VALID_ENTITY_ID)


async def test_process_image(hass, mock_image):
    """Test processing of an image."""
    await async_setup_component(hass, ip.DOMAIN, VALID_CONFIG)
    assert hass.states.get(VALID_ENTITY_ID)

    face_events = []

    @callback
    def mock_face_event(event):
        """Mock event."""
        face_events.append(event)

    hass.bus.async_listen('image_processing.detect_face', mock_face_event)

    with requests_mock.Mocker() as mock_req:
        url = "http://{}:{}/facebox/check".format(MOCK_IP, MOCK_PORT)
        mock_req.post(url, json=MOCK_JSON)
        data = {ATTR_ENTITY_ID: VALID_ENTITY_ID}
        await hass.services.async_call(ip.DOMAIN,
                                       ip.SERVICE_SCAN,
                                       service_data=data)
        await hass.async_block_till_done()

    state = hass.states.get(VALID_ENTITY_ID)
    assert state.state == '1'
    assert state.attributes.get('matched_faces') == MATCHED_FACES

    PARSED_FACES[0][ATTR_ENTITY_ID] = VALID_ENTITY_ID  # Update.
    assert state.attributes.get('faces') == PARSED_FACES
    assert state.attributes.get(CONF_FRIENDLY_NAME) == 'facebox demo_camera'

    assert len(face_events) == 1
    assert face_events[0].data[ATTR_NAME] == PARSED_FACES[0][ATTR_NAME]
    assert (face_events[0].data[fb.ATTR_CONFIDENCE]
            == PARSED_FACES[0][fb.ATTR_CONFIDENCE])
    assert face_events[0].data[ATTR_ENTITY_ID] == VALID_ENTITY_ID
    assert (face_events[0].data[fb.ATTR_IMAGE_ID] ==
            PARSED_FACES[0][fb.ATTR_IMAGE_ID])
    assert (face_events[0].data[fb.ATTR_BOUNDING_BOX] ==
            PARSED_FACES[0][fb.ATTR_BOUNDING_BOX])


async def test_teach_service(hass):
    """Test teaching of facebox."""
    await async_setup_component(hass, ip.DOMAIN, VALID_CONFIG)
    assert hass.states.get(VALID_ENTITY_ID)

    teach_events = []

    @callback
    def mock_teach_event(event):
        """Mock event."""
        teach_events.append(event)

    hass.bus.async_listen(
        'image_processing.teach_classifier', mock_teach_event)

    m_open = mock.mock_open(read_data=b'hello')
    with mock.patch('os.access', mock.Mock(return_value=True)):
        with patch('builtins.open', m_open, create=True):
            with requests_mock.Mocker() as mock_req:
                url = "http://{}:{}/facebox/teach".format(MOCK_IP, MOCK_PORT)
                mock_req.post(url, status_code=200)
                data = {ATTR_ENTITY_ID: VALID_ENTITY_ID,
                        ATTR_NAME: MOCK_NAME,
                        fb.FILE_PATH: MOCK_FILE_PATH}
                await hass.services.async_call(ip.DOMAIN,
                                               fb.SERVICE_FACEBOX_TEACH_FACE,
                                               service_data=data)
                await hass.async_block_till_done()

    assert len(teach_events) == 1
    assert teach_events[0].data[fb.ATTR_CLASSIFIER] == fb.CLASSIFIER
    assert teach_events[0].data[ATTR_NAME] == MOCK_NAME
    assert teach_events[0].data[fb.FILE_PATH] == MOCK_FILE_PATH
    assert teach_events[0].data['success']
    assert not teach_events[0].data['message']

    # Now test the failed teaching.
    with mock.patch('os.access', mock.Mock(return_value=True)):
        with patch('builtins.open', m_open, create=True):
            with requests_mock.Mocker() as mock_req:
                url = "http://{}:{}/facebox/teach".format(MOCK_IP, MOCK_PORT)
                mock_req.post(url, status_code=400, text=MOCK_ERROR)
                data = {ATTR_ENTITY_ID: VALID_ENTITY_ID,
                        ATTR_NAME: MOCK_NAME,
                        fb.FILE_PATH: MOCK_FILE_PATH}
                await hass.services.async_call(ip.DOMAIN,
                                               fb.SERVICE_FACEBOX_TEACH_FACE,
                                               service_data=data)
                await hass.async_block_till_done()

    assert len(teach_events) == 2
    assert teach_events[1].data[fb.ATTR_CLASSIFIER] == fb.CLASSIFIER
    assert teach_events[1].data[ATTR_NAME] == MOCK_NAME
    assert teach_events[1].data[fb.FILE_PATH] == MOCK_FILE_PATH
    assert not teach_events[1].data['success']
    assert teach_events[1].data['message'] == MOCK_ERROR


async def test_connection_error(hass, mock_image):
    """Test connection error."""
    await async_setup_component(hass, ip.DOMAIN, VALID_CONFIG)
    assert hass.states.get(VALID_ENTITY_ID)

    with requests_mock.Mocker() as mock_req:
        url = "http://{}:{}/facebox/check".format(MOCK_IP, MOCK_PORT)
        mock_req.register_uri(
                'POST', url, exc=requests.exceptions.ConnectTimeout)
        data = {ATTR_ENTITY_ID: VALID_ENTITY_ID}
        await hass.services.async_call(ip.DOMAIN,
                                       ip.SERVICE_SCAN,
                                       service_data=data)
        await hass.async_block_till_done()

    state = hass.states.get(VALID_ENTITY_ID)
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get('faces') == []
    assert state.attributes.get('matched_faces') == {}


async def test_setup_platform_with_name(hass):
    """Setup platform with one entity and a name."""
    MOCK_NAME = 'mock_name'
    NAMED_ENTITY_ID = 'image_processing.{}'.format(MOCK_NAME)

    VALID_CONFIG_NAMED = VALID_CONFIG.copy()
    VALID_CONFIG_NAMED[ip.DOMAIN][ip.CONF_SOURCE][ip.CONF_NAME] = MOCK_NAME

    await async_setup_component(hass, ip.DOMAIN, VALID_CONFIG_NAMED)
    assert hass.states.get(NAMED_ENTITY_ID)
    state = hass.states.get(NAMED_ENTITY_ID)
    assert state.attributes.get(CONF_FRIENDLY_NAME) == MOCK_NAME
