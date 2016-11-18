"""The tests for the Script component."""
# pylint: disable=protected-access
import unittest

from homeassistant.core import callback
from homeassistant.bootstrap import setup_component
from homeassistant.components import script

from tests.common import get_test_home_assistant


ENTITY_ID = 'script.test'


class TestScriptComponent(unittest.TestCase):
    """Test the Script component."""

    # pylint: disable=invalid-name
    def setUp(self):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.components.append('group')

    # pylint: disable=invalid-name
    def tearDown(self):
        """Stop down everything that was started."""
        self.hass.stop()

    def test_setup_with_invalid_configs(self):
        """Test setup with invalid configs."""
        for value in (
            {'test': {}},
            {
                'test hello world': {
                    'sequence': [{'event': 'bla'}]
                }
            },
            {
                'test': {
                    'sequence': {
                        'event': 'test_event',
                        'service': 'homeassistant.turn_on',
                    }
                }
            },
        ):
            assert not setup_component(self.hass, 'script', {
                'script': value
            }), 'Script loaded with wrong config {}'.format(value)

            self.assertEqual(0, len(self.hass.states.entity_ids('script')))

    def test_turn_on_service(self):
        """Verify that the turn_on service."""
        event = 'test_event'
        events = []

        @callback
        def record_event(event):
            """Add recorded event to set."""
            events.append(event)

        self.hass.bus.listen(event, record_event)

        assert setup_component(self.hass, 'script', {
            'script': {
                'test': {
                    'sequence': [{
                        'delay': {
                            'seconds': 5
                        }
                    }, {
                        'event': event,
                    }]
                }
            }
        })

        script.turn_on(self.hass, ENTITY_ID)
        self.hass.block_till_done()
        self.assertTrue(script.is_on(self.hass, ENTITY_ID))
        self.assertEqual(0, len(events))

        # Calling turn_on a second time should not advance the script
        script.turn_on(self.hass, ENTITY_ID)
        self.hass.block_till_done()
        self.assertEqual(0, len(events))

        state = self.hass.states.get('group.all_scripts')
        assert state is not None
        assert state.attributes.get('entity_id') == (ENTITY_ID,)

    def test_toggle_service(self):
        """Test the toggling of a service."""
        event = 'test_event'
        events = []

        @callback
        def record_event(event):
            """Add recorded event to set."""
            events.append(event)

        self.hass.bus.listen(event, record_event)

        assert setup_component(self.hass, 'script', {
            'script': {
                'test': {
                    'sequence': [{
                        'delay': {
                            'seconds': 5
                        }
                    }, {
                        'event': event,
                    }]
                }
            }
        })

        script.toggle(self.hass, ENTITY_ID)
        self.hass.block_till_done()
        self.assertTrue(script.is_on(self.hass, ENTITY_ID))
        self.assertEqual(0, len(events))

        script.toggle(self.hass, ENTITY_ID)
        self.hass.block_till_done()
        self.assertFalse(script.is_on(self.hass, ENTITY_ID))
        self.assertEqual(0, len(events))

    def test_passing_variables(self):
        """Test different ways of passing in variables."""
        calls = []

        @callback
        def record_call(service):
            """Add recorded event to set."""
            calls.append(service)

        self.hass.services.register('test', 'script', record_call)

        assert setup_component(self.hass, 'script', {
            'script': {
                'test': {
                    'sequence': {
                        'service': 'test.script',
                        'data_template': {
                            'hello': '{{ greeting }}',
                        },
                    },
                },
            },
        })

        script.turn_on(self.hass, ENTITY_ID, {
            'greeting': 'world'
        })

        self.hass.block_till_done()

        assert len(calls) == 1
        assert calls[-1].data['hello'] == 'world'

        self.hass.services.call('script', 'test', {
            'greeting': 'universe',
        })

        self.hass.block_till_done()

        assert len(calls) == 2
        assert calls[-1].data['hello'] == 'universe'
