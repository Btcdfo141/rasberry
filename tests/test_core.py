"""Test to verify that Home Assistant core works."""
# pylint: disable=protected-access,too-many-public-methods
# pylint: disable=too-few-public-methods
import os
import signal
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta

import pytz

import homeassistant.core as ha
from homeassistant.exceptions import InvalidEntityFormatError
import homeassistant.util.dt as dt_util
from homeassistant.util.unit_system import (METRIC_SYSTEM)
from homeassistant.const import (
    __version__, EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP,
    EVENT_STATE_CHANGED, ATTR_FRIENDLY_NAME, CONF_UNIT_SYSTEM)

from tests.common import get_test_home_assistant

PST = pytz.timezone('America/Los_Angeles')


class TestMethods(unittest.TestCase):
    """Test the Home Assistant helper methods."""

    def test_split_entity_id(self):
        """Test split_entity_id."""
        self.assertEqual(['domain', 'object_id'],
                         ha.split_entity_id('domain.object_id'))


class TestHomeAssistant(unittest.TestCase):
    """Test the Home Assistant core classes."""

    def setUp(self):     # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant(0)

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop everything that was started."""
        self.hass.stop()

    def test_start_and_sigterm(self):
        """Start the test."""
        calls = []
        self.hass.bus.listen_once(EVENT_HOMEASSISTANT_START,
                                  lambda event: calls.append(1))

        self.hass.start()

        self.assertEqual(1, len(calls))

        self.hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP,
                                  lambda event: calls.append(1))

        os.kill(os.getpid(), signal.SIGTERM)

        self.hass.block_till_done()

        self.assertEqual(1, len(calls))


class TestEvent(unittest.TestCase):
    """A Test Event class."""

    def test_eq(self):
        """Test events."""
        now = dt_util.utcnow()
        data = {'some': 'attr'}
        event1, event2 = [
            ha.Event('some_type', data, time_fired=now)
            for _ in range(2)
        ]

        self.assertEqual(event1, event2)

    def test_repr(self):
        """Test that repr method works."""
        self.assertEqual(
            "<Event TestEvent[L]>",
            str(ha.Event("TestEvent")))

        self.assertEqual(
            "<Event TestEvent[R]: beer=nice>",
            str(ha.Event("TestEvent",
                         {"beer": "nice"},
                         ha.EventOrigin.remote)))

    def test_as_dict(self):
        """Test as dictionary."""
        event_type = 'some_type'
        now = dt_util.utcnow()
        data = {'some': 'attr'}

        event = ha.Event(event_type, data, ha.EventOrigin.local, now)
        expected = {
            'event_type': event_type,
            'data': data,
            'origin': 'LOCAL',
            'time_fired': now,
        }
        self.assertEqual(expected, event.as_dict())


class TestEventBus(unittest.TestCase):
    """Test EventBus methods."""

    def setUp(self):     # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.bus = self.hass.bus
        self.bus.listen('test_event', lambda x: len)

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down stuff we started."""
        self.hass.stop()

    def test_add_remove_listener(self):
        """Test remove_listener method."""
        old_count = len(self.bus.listeners)

        def listener(_): pass

        self.bus.listen('test', listener)

        self.assertEqual(old_count + 1, len(self.bus.listeners))

        # Try deleting a non registered listener, nothing should happen
        self.bus._remove_listener('test', lambda x: len)

        # Remove listener
        self.bus._remove_listener('test', listener)
        self.assertEqual(old_count, len(self.bus.listeners))

        # Try deleting listener while category doesn't exist either
        self.bus._remove_listener('test', listener)

    def test_unsubscribe_listener(self):
        """Test unsubscribe listener from returned function."""
        calls = []

        def listener(event):
            """Mock listener."""
            calls.append(event)

        unsub = self.bus.listen('test', listener)

        self.bus.fire('test')
        self.hass.block_till_done()

        assert len(calls) == 1

        unsub()

        self.bus.fire('event')
        self.hass.block_till_done()

        assert len(calls) == 1

    def test_listen_once_event(self):
        """Test listen_once_event method."""
        runs = []

        self.bus.listen_once('test_event', lambda x: runs.append(1))

        self.bus.fire('test_event')
        # Second time it should not increase runs
        self.bus.fire('test_event')

        self.hass.block_till_done()
        self.assertEqual(1, len(runs))


class TestState(unittest.TestCase):
    """Test State methods."""

    def test_init(self):
        """Test state.init."""
        self.assertRaises(
            InvalidEntityFormatError, ha.State,
            'invalid_entity_format', 'test_state')

    def test_domain(self):
        """Test domain."""
        state = ha.State('some_domain.hello', 'world')
        self.assertEqual('some_domain', state.domain)

    def test_object_id(self):
        """Test object ID."""
        state = ha.State('domain.hello', 'world')
        self.assertEqual('hello', state.object_id)

    def test_name_if_no_friendly_name_attr(self):
        """Test if there is no friendly name."""
        state = ha.State('domain.hello_world', 'world')
        self.assertEqual('hello world', state.name)

    def test_name_if_friendly_name_attr(self):
        """Test if there is a friendly name."""
        name = 'Some Unique Name'
        state = ha.State('domain.hello_world', 'world',
                         {ATTR_FRIENDLY_NAME: name})
        self.assertEqual(name, state.name)

    def test_dict_conversion(self):
        """Test conversion of dict."""
        state = ha.State('domain.hello', 'world', {'some': 'attr'})
        self.assertEqual(state, ha.State.from_dict(state.as_dict()))

    def test_dict_conversion_with_wrong_data(self):
        """Test conversion with wrong data."""
        self.assertIsNone(ha.State.from_dict(None))
        self.assertIsNone(ha.State.from_dict({'state': 'yes'}))
        self.assertIsNone(ha.State.from_dict({'entity_id': 'yes'}))

    def test_repr(self):
        """Test state.repr."""
        self.assertEqual("<state happy.happy=on @ 1984-12-08T12:00:00+00:00>",
                         str(ha.State(
                             "happy.happy", "on",
                             last_changed=datetime(1984, 12, 8, 12, 0, 0))))

        self.assertEqual(
            "<state happy.happy=on; brightness=144 @ "
            "1984-12-08T12:00:00+00:00>",
            str(ha.State("happy.happy", "on", {"brightness": 144},
                         datetime(1984, 12, 8, 12, 0, 0))))


class TestStateMachine(unittest.TestCase):
    """Test State machine methods."""

    def setUp(self):    # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant(0)
        self.states = self.hass.states
        self.states.set("light.Bowl", "on")
        self.states.set("switch.AC", "off")

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down stuff we started."""
        self.hass.stop()

    def test_is_state(self):
        """Test is_state method."""
        self.assertTrue(self.states.is_state('light.Bowl', 'on'))
        self.assertFalse(self.states.is_state('light.Bowl', 'off'))
        self.assertFalse(self.states.is_state('light.Non_existing', 'on'))

    def test_is_state_attr(self):
        """Test is_state_attr method."""
        self.states.set("light.Bowl", "on", {"brightness": 100})
        self.assertTrue(
            self.states.is_state_attr('light.Bowl', 'brightness', 100))
        self.assertFalse(
            self.states.is_state_attr('light.Bowl', 'friendly_name', 200))
        self.assertFalse(
            self.states.is_state_attr('light.Bowl', 'friendly_name', 'Bowl'))
        self.assertFalse(
            self.states.is_state_attr('light.Non_existing', 'brightness', 100))

    def test_entity_ids(self):
        """Test get_entity_ids method."""
        ent_ids = self.states.entity_ids()
        self.assertEqual(2, len(ent_ids))
        self.assertTrue('light.bowl' in ent_ids)
        self.assertTrue('switch.ac' in ent_ids)

        ent_ids = self.states.entity_ids('light')
        self.assertEqual(1, len(ent_ids))
        self.assertTrue('light.bowl' in ent_ids)

    def test_all(self):
        """Test everything."""
        states = sorted(state.entity_id for state in self.states.all())
        self.assertEqual(['light.bowl', 'switch.ac'], states)

    def test_remove(self):
        """Test remove method."""
        events = []
        self.hass.bus.listen(EVENT_STATE_CHANGED,
                             lambda event: events.append(event))

        self.assertIn('light.bowl', self.states.entity_ids())
        self.assertTrue(self.states.remove('light.bowl'))
        self.hass.block_till_done()

        self.assertNotIn('light.bowl', self.states.entity_ids())
        self.assertEqual(1, len(events))
        self.assertEqual('light.bowl', events[0].data.get('entity_id'))
        self.assertIsNotNone(events[0].data.get('old_state'))
        self.assertEqual('light.bowl', events[0].data['old_state'].entity_id)
        self.assertIsNone(events[0].data.get('new_state'))

        # If it does not exist, we should get False
        self.assertFalse(self.states.remove('light.Bowl'))
        self.hass.block_till_done()
        self.assertEqual(1, len(events))

    def test_case_insensitivty(self):
        """Test insensitivty."""
        runs = []

        self.hass.bus.listen(EVENT_STATE_CHANGED,
                             lambda event: runs.append(event))

        self.states.set('light.BOWL', 'off')
        self.hass.block_till_done()

        self.assertTrue(self.states.is_state('light.bowl', 'off'))
        self.assertEqual(1, len(runs))

    def test_last_changed_not_updated_on_same_state(self):
        """Test to not update the existing, same state."""
        state = self.states.get('light.Bowl')

        future = dt_util.utcnow() + timedelta(hours=10)

        with patch('homeassistant.util.dt.utcnow', return_value=future):
            self.states.set("light.Bowl", "on", {'attr': 'triggers_change'})
            self.hass.block_till_done()

        state2 = self.states.get('light.Bowl')
        assert state2 is not None
        assert state.last_changed == state2.last_changed

    def test_force_update(self):
        """Test force update option."""
        events = []
        self.hass.bus.listen(EVENT_STATE_CHANGED, events.append)

        self.states.set('light.bowl', 'on')
        self.hass.block_till_done()
        self.assertEqual(0, len(events))

        self.states.set('light.bowl', 'on', None, True)
        self.hass.block_till_done()
        self.assertEqual(1, len(events))


class TestServiceCall(unittest.TestCase):
    """Test ServiceCall class."""

    def test_repr(self):
        """Test repr method."""
        self.assertEqual(
            "<ServiceCall homeassistant.start>",
            str(ha.ServiceCall('homeassistant', 'start')))

        self.assertEqual(
            "<ServiceCall homeassistant.start: fast=yes>",
            str(ha.ServiceCall('homeassistant', 'start', {"fast": "yes"})))


class TestServiceRegistry(unittest.TestCase):
    """Test ServicerRegistry methods."""

    def setUp(self):     # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.services = self.hass.services
        self.services.register("Test_Domain", "TEST_SERVICE", lambda x: None)
        self.hass.block_till_done()

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down stuff we started."""
        self.hass.stop()

    def test_has_service(self):
        """Test has_service method."""
        self.assertTrue(
            self.services.has_service("tesT_domaiN", "tesT_servicE"))
        self.assertFalse(
            self.services.has_service("test_domain", "non_existing"))
        self.assertFalse(
            self.services.has_service("non_existing", "test_service"))

    def test_services(self):
        """Test services."""
        expected = {
            'test_domain': {'test_service': {'description': '', 'fields': {}}}
        }
        self.assertEqual(expected, self.services.services)

    def test_call_with_blocking_done_in_time(self):
        """Test call with blocking."""
        calls = []
        self.services.register("test_domain", "register_calls",
                               lambda x: calls.append(1))

        self.assertTrue(
            self.services.call('test_domain', 'REGISTER_CALLS', blocking=True))
        self.assertEqual(1, len(calls))

    def test_call_non_existing_with_blocking(self):
        """Test non-existing with blocking."""
        ha.SERVICE_CALL_LIMIT = 0.01
        assert not self.services.call('test_domain', 'i_do_not_exist',
                                      blocking=True)


class TestConfig(unittest.TestCase):
    """Test configuration methods."""

    def setUp(self):     # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.config = ha.Config()
        self.assertIsNone(self.config.config_dir)

    def test_path_with_file(self):
        """Test get_config_path method."""
        self.config.config_dir = '/tmp/ha-config'
        self.assertEqual("/tmp/ha-config/test.conf",
                         self.config.path("test.conf"))

    def test_path_with_dir_and_file(self):
        """Test get_config_path method."""
        self.config.config_dir = '/tmp/ha-config'
        self.assertEqual("/tmp/ha-config/dir/test.conf",
                         self.config.path("dir", "test.conf"))

    def test_as_dict(self):
        """Test as dict."""
        expected = {
            'latitude': None,
            'longitude': None,
            CONF_UNIT_SYSTEM: METRIC_SYSTEM.as_dict(),
            'location_name': None,
            'time_zone': 'UTC',
            'components': [],
            'version': __version__,
        }

        self.assertEqual(expected, self.config.as_dict())


class TestWorkerPool(unittest.TestCase):
    """Test WorkerPool methods."""

    def test_exception_during_job(self):
        """Test exception during a job."""
        pool = ha.create_worker_pool(1)

        def malicious_job(_):
            raise Exception("Test breaking worker pool")

        calls = []

        def register_call(_):
            calls.append(1)

        pool.add_job(ha.JobPriority.EVENT_DEFAULT, (malicious_job, None))
        pool.add_job(ha.JobPriority.EVENT_DEFAULT, (register_call, None))
        pool.block_till_done()
        self.assertEqual(1, len(calls))
