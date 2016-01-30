"""
tests.helpers.test_service
~~~~~~~~~~~~~~~~~~~~~~~~~~

Test service helpers.
"""
import unittest
from unittest.mock import patch

from homeassistant import core as ha, loader
from homeassistant.const import STATE_ON, STATE_OFF, ATTR_ENTITY_ID
from homeassistant.helpers import service

from tests.common import get_test_home_assistant, mock_service


class TestServiceHelpers(unittest.TestCase):
    """
    Tests the Home Assistant service helpers.
    """

    def setUp(self):     # pylint: disable=invalid-name
        """ things to be run when tests are started. """
        self.hass = get_test_home_assistant()
        self.calls = mock_service(self.hass, 'test_domain', 'test_service')

        service.HASS = self.hass

    def tearDown(self):  # pylint: disable=invalid-name
        """ Stop down stuff we started. """
        self.hass.stop()

    def test_service(self):
        """ Test service registration decorator. """
        runs = []

        decor = service.service('test', 'test')
        decor(lambda x, y: runs.append(1))

        self.hass.services.call('test', 'test')
        self.hass.pool.block_till_done()
        self.assertEqual(1, len(runs))

    def test_split_entity_string(self):
        service.call_from_config(self.hass, {
            'service': 'test_domain.test_service',
            'entity_id': 'hello.world, sensor.beer'
        })
        self.hass.pool.block_till_done()
        self.assertEqual(['hello.world', 'sensor.beer'],
                         self.calls[-1].data.get('entity_id'))

    def test_not_mutate_input(self):
        orig = {
            'service': 'test_domain.test_service',
            'entity_id': 'hello.world, sensor.beer',
            'data': {
                'hello': 1,
            },
        }
        service.call_from_config(self.hass, orig)
        self.hass.pool.block_till_done()
        self.assertEqual({
            'service': 'test_domain.test_service',
            'entity_id': 'hello.world, sensor.beer',
            'data': {
                'hello': 1,
            },
        }, orig)

    @patch('homeassistant.helpers.service._LOGGER.error')
    def test_fail_silently_if_no_service(self, mock_log):
        service.call_from_config(self.hass, None)
        self.assertEqual(1, mock_log.call_count)

        service.call_from_config(self.hass, {})
        self.assertEqual(2, mock_log.call_count)

        service.call_from_config(self.hass, {
            'service': 'invalid'
        })
        self.assertEqual(3, mock_log.call_count)

    def test_extract_entity_ids(self):
        """ Test extract_entity_ids method. """
        self.hass.states.set('light.Bowl', STATE_ON)
        self.hass.states.set('light.Ceiling', STATE_OFF)
        self.hass.states.set('light.Kitchen', STATE_OFF)

        loader.get_component('group').Group(
            self.hass, 'test', ['light.Ceiling', 'light.Kitchen'])

        call = ha.ServiceCall('light', 'turn_on',
                              {ATTR_ENTITY_ID: 'light.Bowl'})

        self.assertEqual(['light.bowl'],
                         service.extract_entity_ids(self.hass, call))

        call = ha.ServiceCall('light', 'turn_on',
                              {ATTR_ENTITY_ID: 'group.test'})

        self.assertEqual(['light.ceiling', 'light.kitchen'],
                         service.extract_entity_ids(self.hass, call))
