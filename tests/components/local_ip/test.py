"""Tests for the localip component."""
import pytest

from homeassistant.components.localip import DOMAIN
from homeassistant.setup import async_setup_component
from homeassistant.util import get_local_ip


@pytest.fixture(name="config")
def config_fixture():
    """Create hass config fixture."""
    return {DOMAIN: {"name": "test"}}


async def test_basic_setup(hass, config):
    """Test component setup creates entry from config."""
    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()
    local_ip = get_local_ip()
    state = hass.states.get("sensor.test")
    assert state
    assert state.state == local_ip
