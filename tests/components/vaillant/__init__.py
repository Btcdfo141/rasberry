"""The tests for vaillant platforms."""
import datetime

import mock
from vr900connector.model import System, BoilerStatus, Zone, HeatingMode, \
    Room, Device, HotWater, Circulation, TimeProgramDaySetting, \
    TimeProgramDay, TimeProgram

from homeassistant.components.vaillant import DOMAIN
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.setup import async_setup_component
from homeassistant.util import utcnow
from tests.common import async_fire_time_changed

VALID_MINIMAL_CONFIG = {
    DOMAIN: {
        CONF_USERNAME: 'test',
        CONF_PASSWORD: 'test'
    }
}


class SystemManagerMock:
    """Mock the vaillant system manager."""

    system = None
    instance = None

    @classmethod
    def reset(cls):
        """Reset system the mock."""
        cls.system = None
        cls.instance = None

    @classmethod
    def time_program(cls, heating_mode=HeatingMode.OFF, temp=20):
        """Create a default time program."""
        timeprogram_day_setting = TimeProgramDaySetting('00:00', temp,
                                                        heating_mode)
        timeprogram_day = TimeProgramDay([timeprogram_day_setting])
        timeprogram_days = {
            'monday': timeprogram_day,
            'tuesday': timeprogram_day,
            'wednesday': timeprogram_day,
            'thursday': timeprogram_day,
            'friday': timeprogram_day,
            'saturday': timeprogram_day,
            'sunday': timeprogram_day,
        }
        return TimeProgram(timeprogram_days)

    @classmethod
    def get_default_system(cls):
        """Return default system."""
        holiday_mode = None
        boiler_status = BoilerStatus('boiler', 'Long description',
                                     'short description', 'S.31', 'hint',
                                     datetime.datetime.now(), 'ONLINE',
                                     'UPDATE_NOT_PENDING', 1.4, 20)

        zone = Zone('zone_1', 'Zone 1', cls.time_program(), 25, 30,
                    HeatingMode.AUTO, None, 22, 'heating', False)

        room_device = Device('Device 1', '123456789', 'VALVE', False, False)
        room = Room(1, 'Room 1', cls.time_program(), 22, 24,
                    HeatingMode.AUTO, None, False, False, [room_device])

        hot_water = HotWater('hot_water', 'Hot water',
                             cls.time_program(temp=None), 45, 40,
                             HeatingMode.AUTO)

        circulation = Circulation('circulation', 'Circulation',
                                  cls.time_program(), HeatingMode.AUTO)

        outdoor_temp = 18
        quick_mode = None

        return System(holiday_mode, boiler_status, [zone], [room], hot_water,
                      circulation, outdoor_temp, quick_mode, [])

    @classmethod
    def _init_mocks_function(cls):
        """Init the instance."""
        if not cls.system:
            cls.system = cls.get_default_system()

        cls.instance.set_hot_water_setpoint_temperature = \
            mock.MagicMock(return_value=True)
        cls.instance.set_hot_water_operation_mode = \
            mock.MagicMock(return_value=True)
        cls.instance.set_hot_water_operation_mode = mock.MagicMock()
        cls.instance.get_hot_water = mock.MagicMock()
        cls.instance.request_hvac_update = mock.MagicMock(return_value=True)
        cls.instance.get_system = \
            mock.MagicMock(return_value=cls.system)

    def __init__(self, user: str, password: str, smart_phone_id: str,
                 file_path: str = None):
        """Mock the constructor."""
        SystemManagerMock.instance = self
        self._init_mocks_function()

    # def get_system(self):
    #     """Return mock system."""
    #     return self.system
    #
    # def request_hvac_update(self):
    #     """Mock request_hvac_update."""
    #     return True


async def _goto_future(hass, future=None):
    """Move to future."""
    if not future:
        future = utcnow() + datetime.timedelta(minutes=5)
    with mock.patch('homeassistant.util.utcnow', return_value=future):
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()


async def _setup(hass, config=None, system=None):
    """Set up vaillant component."""
    if not config:
        config = VALID_MINIMAL_CONFIG
    if not system:
        system = SystemManagerMock.get_default_system()
    SystemManagerMock.system = system
    setup = await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()
    return setup
