"""The test for the geo rss events sensor platform."""
import unittest
from unittest import mock
import feedparser

from homeassistant.setup import setup_component
from tests.common import load_fixture, get_test_home_assistant
import homeassistant.components.sensor.geo_rss_events as geo_rss_events

URL = 'http://geo.rss.local/geo_rss_events.xml'
VALID_CONFIG_WITH_CATEGORIES = {
    'platform': 'geo_rss_events',
    geo_rss_events.CONF_URL: URL,
    geo_rss_events.CONF_CATEGORIES: [
        'Category 1',
        'Category 2'
    ]
}
VALID_CONFIG_WITHOUT_CATEGORIES = {
    'platform': 'geo_rss_events',
    geo_rss_events.CONF_URL: URL
}


class TestGeoRssServiceUpdater(unittest.TestCase):
    """Test the GeoRss service updater."""

    def setUp(self):
        """Initialize values for this testcase class."""
        self.hass = get_test_home_assistant()
        self.config = VALID_CONFIG_WITHOUT_CATEGORIES

    def tearDown(self):
        """Stop everything that was started."""
        self.hass.stop()

    @mock.patch('feedparser.parse', return_value=feedparser.parse(""))
    def test_setup_with_categories(self, mock_parse):
        """Test the general setup of this sensor."""
        self.config = VALID_CONFIG_WITH_CATEGORIES
        self.assertTrue(
            setup_component(self.hass, 'sensor', {'sensor': self.config}))
        self.assertIsNotNone(
            self.hass.states.get('sensor.event_service_category_1'))
        self.assertIsNotNone(
            self.hass.states.get('sensor.event_service_category_2'))

    @mock.patch('feedparser.parse', return_value=feedparser.parse(""))
    def test_setup_without_categories(self, mock_parse):
        """Test the general setup of this sensor."""
        self.assertTrue(
            setup_component(self.hass, 'sensor', {'sensor': self.config}))
        self.assertIsNotNone(self.hass.states.get('sensor.event_service_any'))

    def setup_data(self, url='url', custom_attributes_definition=None,
                   custom_filters_definition=None):
        """Set up data object for use by sensors."""
        if custom_attributes_definition is None:
            custom_attributes_definition = []
        home_latitude = -33.865
        home_longitude = 151.209444
        radius_in_km = 500
        data = geo_rss_events.GeoRssServiceData(home_latitude,
                                                home_longitude, url,
                                                radius_in_km,
                                                custom_attributes_definition,
                                                custom_filters_definition)
        return data

    def test_update_sensor_with_category(self):
        """Test updating sensor object."""
        raw_data = load_fixture('geo_rss_events.xml')
        # Loading raw data from fixture and plug in to data object as URL
        # works since the third-party feedparser library accepts a URL
        # as well as the actual data.
        data = self.setup_data(raw_data)
        category = "Category 1"
        name = "Name 1"
        unit_of_measurement = "Unit 1"
        sort_reverse = False
        publish_events = False
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement, None,
                                                    sort_reverse,
                                                    publish_events)

        sensor.update()
        assert sensor.name == "Name 1 Category 1"
        assert sensor.unit_of_measurement == "Unit 1"
        assert sensor.icon == "mdi:alert"
        assert len(sensor._data.events) == 4
        assert sensor.state == 1
        assert sensor.device_state_attributes == {'Title 1': "117km"}
        # Check entries of first hit
        assert sensor._data.events[0][geo_rss_events.ATTR_TITLE] == "Title 1"
        assert sensor._data.events[0][
                   geo_rss_events.ATTR_CATEGORY] == "Category 1"
        self.assertAlmostEqual(sensor._data.events[0][
                                   geo_rss_events.ATTR_DISTANCE], 116.586, 0)

    def test_update_sensor_without_category(self):
        """Test updating sensor object."""
        raw_data = load_fixture('geo_rss_events.xml')
        data = self.setup_data(raw_data)
        category = None
        name = "Name 2"
        unit_of_measurement = "Unit 2"
        sort_reverse = False
        publish_events = False
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement, None,
                                                    sort_reverse,
                                                    publish_events)

        sensor.update()
        assert sensor.name == "Name 2 Any"
        assert sensor.unit_of_measurement == "Unit 2"
        assert sensor.icon == "mdi:alert"
        assert len(sensor._data.events) == 4
        assert sensor.state == 4
        assert sensor.device_state_attributes == {'Title 1': "117km",
                                                  'Title 2': "302km",
                                                  'Title 3': "204km",
                                                  'Title 6': "48km"}

    def test_update_sensor_without_data(self):
        """Test updating sensor object."""
        data = self.setup_data()
        category = None
        name = "Name 3"
        unit_of_measurement = "Unit 3"
        sort_reverse = False
        publish_events = False
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement, None,
                                                    sort_reverse,
                                                    publish_events)

        sensor.update()
        assert sensor.name == "Name 3 Any"
        assert sensor.unit_of_measurement == "Unit 3"
        assert sensor.icon == "mdi:alert"
        assert len(sensor._data.events) == 0
        assert sensor.state == 0

    @mock.patch('feedparser.parse', return_value=None)
    def test_update_sensor_with_none_result(self, parse_function):
        """Test updating sensor object."""
        data = self.setup_data("http://invalid.url/")
        category = None
        name = "Name 4"
        unit_of_measurement = "Unit 4"
        sort_reverse = False
        publish_events = False
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement, None,
                                                    sort_reverse,
                                                    publish_events)

        sensor.update()
        assert sensor.name == "Name 4 Any"
        assert sensor.unit_of_measurement == "Unit 4"
        assert sensor.state == 0

    def test_sort_by_distance(self):
        """Test sorting entries by distance."""
        raw_data = load_fixture('geo_rss_events.xml')
        data = self.setup_data(raw_data)
        category = None
        name = "Name 2"
        unit_of_measurement = "Unit 2"
        sort_by = "distance"
        sort_reverse = False
        publish_events = False
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement,
                                                    sort_by, sort_reverse,
                                                    publish_events)
        sensor.update()
        assert sensor.state == 4
        assert str(sensor.device_state_attributes) == str({'Title 6': "48km",
                                                           'Title 1': "117km",
                                                           'Title 3': "204km",
                                                           'Title 2': "302km"})
        # Test reverse sort order
        sort_reverse = True
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement,
                                                    sort_by, sort_reverse,
                                                    publish_events)
        sensor.update()
        assert sensor.state == 4
        assert str(sensor.device_state_attributes) == str({'Title 2': "302km",
                                                           'Title 3': "204km",
                                                           'Title 1': "117km",
                                                           'Title 6': "48km"})

    def test_sort_by_date_published(self):
        """Test sorting entries by published date."""
        raw_data = load_fixture('geo_rss_events.xml')
        data = self.setup_data(raw_data)
        category = None
        name = "Name 2"
        unit_of_measurement = "Unit 2"
        sort_by = "date_published"
        sort_reverse = False
        publish_events = False
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement,
                                                    sort_by, sort_reverse,
                                                    publish_events)
        sensor.update()
        assert sensor.state == 4
        assert str(sensor.device_state_attributes) == str({'Title 6': "48km",
                                                           'Title 1': "117km",
                                                           'Title 2': "302km",
                                                           'Title 3': "204km"})
        # Test reverse sort order
        sort_reverse = True
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement,
                                                    sort_by, sort_reverse,
                                                    publish_events)
        sensor.update()
        assert sensor.state == 4
        assert str(sensor.device_state_attributes) == str({'Title 3': "204km",
                                                           'Title 2': "302km",
                                                           'Title 1': "117km",
                                                           'Title 6': "48km"})

    def test_sort_by_date_updated(self):
        """Test sorting entries by updated date."""
        raw_data = load_fixture('geo_rss_events.xml')
        data = self.setup_data(raw_data)
        category = None
        name = "Name 2"
        unit_of_measurement = "Unit 2"
        sort_by = "date_updated"
        sort_reverse = False
        publish_events = False
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement,
                                                    sort_by, sort_reverse,
                                                    publish_events)
        sensor.update()
        assert sensor.state == 4
        assert str(sensor.device_state_attributes) == str({'Title 2': "302km",
                                                           'Title 3': "204km",
                                                           'Title 1': "117km",
                                                           'Title 6': "48km"})
        # Test reverse sort order
        sort_reverse = True
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement,
                                                    sort_by, sort_reverse,
                                                    publish_events)
        sensor.update()
        assert sensor.state == 4
        assert str(sensor.device_state_attributes) == str({'Title 6': "48km",
                                                           'Title 1': "117km",
                                                           'Title 3': "204km",
                                                           'Title 2': "302km"})

    def test_custom_attributes(self):
        """Test extracting a custom attribute."""
        raw_data = load_fixture('geo_rss_events.xml')
        custom_attributes_definition = [{
            geo_rss_events.CONF_CUSTOM_ATTRIBUTES_NAME: 'title_index',
            geo_rss_events.CONF_CUSTOM_ATTRIBUTES_SOURCE: 'title',
            geo_rss_events.CONF_CUSTOM_ATTRIBUTES_REGEXP:
                '(?P<custom_attribute>\d+)'
        }]
        data = self.setup_data(raw_data, custom_attributes_definition)
        data.update()
        assert data.events[0]['title_index'] == '1'
        assert data.events[1]['title_index'] == '2'
        assert data.events[2]['title_index'] == '3'
        assert data.events[3]['title_index'] == '6'

    def test_custom_attributes_nonexistent_source(self):
        """Test extracting a custom attribute from a nonexistent source."""
        raw_data = load_fixture('geo_rss_events.xml')
        custom_attributes_definition = [{
            geo_rss_events.CONF_CUSTOM_ATTRIBUTES_NAME: 'title_index',
            geo_rss_events.CONF_CUSTOM_ATTRIBUTES_SOURCE: 'nonexistent',
            geo_rss_events.CONF_CUSTOM_ATTRIBUTES_REGEXP:
                '(?P<custom_attribute>\d+)'
        }]
        data = self.setup_data(raw_data, custom_attributes_definition)
        data.update()
        assert data.events[0]['title_index'] is None
        assert data.events[1]['title_index'] is None
        assert data.events[2]['title_index'] is None
        assert data.events[3]['title_index'] is None

    def test_sort_by_custom_attributes(self):
        """Extract a custom attribute and sort events by that attribute."""
        raw_data = load_fixture('geo_rss_events.xml')
        custom_attributes_definition = [{
            geo_rss_events.CONF_CUSTOM_ATTRIBUTES_NAME: 'title_index',
            geo_rss_events.CONF_CUSTOM_ATTRIBUTES_SOURCE: 'title',
            geo_rss_events.CONF_CUSTOM_ATTRIBUTES_REGEXP:
                '(?P<custom_attribute>\d+)'
        }]
        data = self.setup_data(raw_data, custom_attributes_definition)
        category = None
        name = "Name 2"
        unit_of_measurement = "Unit 2"
        sort_by = "title_index"
        sort_reverse = False
        publish_events = False
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement,
                                                    sort_by, sort_reverse,
                                                    publish_events)
        sensor.update()
        assert sensor.state == 4
        assert str(sensor.device_state_attributes) == str({'Title 1': "117km",
                                                           'Title 2': "302km",
                                                           'Title 3': "204km",
                                                           'Title 6': "48km"})
        # Test reverse sort order
        sort_reverse = True
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement,
                                                    sort_by, sort_reverse,
                                                    publish_events)
        sensor.update()
        assert sensor.state == 4
        assert str(sensor.device_state_attributes) == str({'Title 6': "48km",
                                                           'Title 3': "204km",
                                                           'Title 2': "302km",
                                                           'Title 1': "117km"})

    def test_custom_filter(self):
        """Test a custom filter."""
        raw_data = load_fixture('geo_rss_events.xml')
        custom_filter_definition = [{
            geo_rss_events.CONF_CUSTOM_FILTERS_ATTRIBUTE: 'title',
            geo_rss_events.CONF_CUSTOM_FILTERS_REGEXP:
                'Title [3-9]{1}'
        }]
        data = self.setup_data(raw_data, None, custom_filter_definition)
        data.update()
        assert data.events[0]['title'] == 'Title 3'
        assert data.events[1]['title'] == 'Title 6'

    def test_send_events(self):
        """Test sending events to the event bus."""
        raw_data = load_fixture('geo_rss_events.xml')
        data = self.setup_data(raw_data)
        category = None
        name = "Name 1"
        unit_of_measurement = "Unit 1"
        sort_by = None
        sort_reverse = False
        publish_events = True
        sensor = geo_rss_events.GeoRssServiceSensor(self.hass, category,
                                                    data, name,
                                                    unit_of_measurement,
                                                    sort_by, sort_reverse,
                                                    publish_events)
        # Set up event listener
        events = []

        def listener(event):
            events.append(event)

        self.hass.bus.async_listen(sensor._event_type_id, listener)
        # Update sensor and this trigger publishing events.
        sensor.update()
        self.hass.block_till_done()

        assert len(events) == 4

        # Read second event file with updated events.
        raw_data = load_fixture('geo_rss_events2.xml')
        data = self.setup_data(raw_data)
        sensor._data = data
        events = []
        sensor.update()
        self.hass.block_till_done()

        assert len(events) == 3
