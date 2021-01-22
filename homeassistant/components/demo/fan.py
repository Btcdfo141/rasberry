"""Demo fan platform that has a fake fan."""
from homeassistant.components.fan import (
    SPEED_HIGH,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_OFF,
    SUPPORT_DIRECTION,
    SUPPORT_OSCILLATE,
    SUPPORT_SET_SPEED,
    FanEntity,
    percentage_compat,
    speed_compat,
)

FULL_SUPPORT = SUPPORT_SET_SPEED | SUPPORT_OSCILLATE | SUPPORT_DIRECTION
LIMITED_SUPPORT = SUPPORT_SET_SPEED


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the demo fan platform."""
    async_add_entities(
        [
            DemoFan(hass, "fan1", "Living Room Fan", FULL_SUPPORT),
            DemoFan(hass, "fan2", "Ceiling Fan", LIMITED_SUPPORT),
            AsyncDemoPercentageFan(hass, "fan3", "Percentage Full Fan", FULL_SUPPORT),
            DemoPercentageFan(hass, "fan4", "Percentage Limited Fan", LIMITED_SUPPORT),
        ]
    )


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Demo config entry."""
    await async_setup_platform(hass, {}, async_add_entities)


class BaseDemoFan(FanEntity):
    """A demonstration fan component that uses legacy fan speeds."""

    def __init__(
        self, hass, unique_id: str, name: str, supported_features: int
    ) -> None:
        """Initialize the entity."""
        self.hass = hass
        self._unique_id = unique_id
        self._supported_features = supported_features
        self._speed = SPEED_OFF
        self._percentage = 0
        self._oscillating = None
        self._direction = None
        self._name = name
        if supported_features & SUPPORT_OSCILLATE:
            self._oscillating = False
        if supported_features & SUPPORT_DIRECTION:
            self._direction = "forward"

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Get entity name."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed for a demo fan."""
        return False

    @property
    def current_direction(self) -> str:
        """Fan direction."""
        return self._direction

    @property
    def oscillating(self) -> bool:
        """Oscillating."""
        return self._oscillating

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features


class DemoFan(BaseDemoFan, FanEntity):
    """A demonstration fan component that uses legacy fan speeds."""

    @property
    def speed(self) -> str:
        """Return the current speed."""
        return self._speed

    @property
    def speed_list(self) -> list:
        """Get the list of available speeds."""
        return [SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH]

    @percentage_compat
    def turn_on(self, speed: str = None, percentage: int = None, **kwargs) -> None:
        """Turn on the entity."""
        if speed is None:
            speed = SPEED_MEDIUM
        self.set_speed(speed)

    def turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        self.oscillate(False)
        self.set_speed(SPEED_OFF)

    def set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        self._speed = speed
        self.schedule_update_ha_state()

    def set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        self._direction = direction
        self.schedule_update_ha_state()

    def oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        self._oscillating = oscillating
        self.schedule_update_ha_state()


class DemoPercentageFan(BaseDemoFan, FanEntity):
    """A demonstration fan component that uses percentages."""

    @property
    def percentage(self) -> str:
        """Return the current speed."""
        return self._percentage

    def set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        self._percentage = percentage
        self.schedule_update_ha_state()

    @speed_compat
    def turn_on(self, speed: str = None, percentage: int = None, **kwargs) -> None:
        """Turn on the entity."""
        if percentage is None:
            percentage = 67

        self.set_percentage(percentage)

    def turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        self.set_percentage(0)


class AsyncDemoPercentageFan(BaseDemoFan, FanEntity):
    """An async demonstration fan component that uses percentages."""

    @property
    def percentage(self) -> str:
        """Return the current speed."""
        return self._percentage

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        self._percentage = percentage
        self.async_write_ha_state()

    @speed_compat
    async def async_turn_on(
        self, speed: str = None, percentage: int = None, **kwargs
    ) -> None:
        """Turn on the entity."""
        if percentage is None:
            percentage = 67

        await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        await self.async_oscillate(False)
        await self.async_set_percentage(0)

    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        self._direction = direction
        self.async_write_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        self._oscillating = oscillating
        self.async_write_ha_state()
