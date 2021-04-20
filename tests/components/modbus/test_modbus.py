"""The tests for the Modbus sensor component."""
import logging
from unittest import mock

from pymodbus.exceptions import ModbusException
import pytest

from homeassistant.components.modbus.const import (
    ATTR_ADDRESS,
    ATTR_HUB,
    ATTR_STATE,
    ATTR_UNIT,
    ATTR_VALUE,
    DEFAULT_HUB,
    MODBUS_DOMAIN as DOMAIN,
    SERVICE_WRITE_COIL,
    SERVICE_WRITE_REGISTER,
)
from homeassistant.components.modbus.modbus import ModbusHub
from homeassistant.const import (
    CONF_DELAY,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_TYPE,
)
from homeassistant.setup import async_setup_component

from .conftest import ReadResult


@pytest.fixture()
def modbus_hub():
    """Return class obj configured."""

    config_hub = {
        CONF_NAME: DEFAULT_HUB,
        CONF_TYPE: "tcp",
        CONF_HOST: "modbusTest",
        CONF_PORT: 5001,
        CONF_DELAY: 1,
        CONF_TIMEOUT: 1,
    }
    hub = ModbusHub(config_hub)
    assert hub.name == config_hub[CONF_NAME]
    return hub


async def test_pb_create_exception(hass, caplog, modbus_hub):
    """Run general test of class modbusHub."""

    with mock.patch(
        "homeassistant.components.modbus.modbus.ModbusTcpClient"
    ) as mock_pb:
        caplog.set_level(logging.DEBUG)
        mock_pb.side_effect = ModbusException("test no class")
        modbus_hub.setup()
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"


async def test_pb_connect(hass, caplog, modbus_hub):
    """Run general test of class modbusHub."""

    mock_pb = mock.MagicMock()
    with mock.patch(
        "homeassistant.components.modbus.modbus.ModbusTcpClient", return_value=mock_pb
    ):
        caplog.set_level(logging.DEBUG)
        modbus_hub.setup()
        assert mock_pb.connect.called
        assert len(caplog.records) == 0
        caplog.clear()

        mock_pb.connect.side_effect = ModbusException("test failed connect()")
        modbus_hub.setup()
        assert mock_pb.connect.called
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"


async def test_pb_close(hass, caplog, modbus_hub):
    """Run general test of class modbusHub."""

    caplog.set_level(logging.DEBUG)
    mock_pb = mock.MagicMock()
    with mock.patch(
        "homeassistant.components.modbus.modbus.ModbusTcpClient", return_value=mock_pb
    ):
        caplog.clear()
        modbus_hub.setup()
        modbus_hub.close()
        assert mock_pb.close.called
        assert len(caplog.records) == 0

        mock_pb.close.side_effect = ModbusException("test failed close()")
        modbus_hub.setup()
        caplog.clear()
        modbus_hub.close()
        assert mock_pb.close.called
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"


async def test_pb_read_coils(hass, modbus_hub):
    """Run test for pymodbus read_coils calls."""

    mock_pb = mock.MagicMock()
    with mock.patch(
        "homeassistant.components.modbus.modbus.ModbusTcpClient", return_value=mock_pb
    ):
        modbus_hub.setup()

        data = [0x15]
        mock_pb.read_coils.return_value = ReadResult(data)
        result = modbus_hub.read_coils(None, 17, 1)
        assert result.registers == data

        data = [0x15, 0x16]
        mock_pb.read_coils.return_value = ReadResult(data)
        result = modbus_hub.read_coils(None, 17, 2)
        assert result.registers == data

        data = [0x15, 0x16]
        mock_pb.read_coils.side_effect = ModbusException("fail read_coils")
        result = modbus_hub.read_coils(None, 17, 2)
        assert result is None


async def test_pb_read_discrete_inputs(hass, modbus_hub):
    """Run test for pymodbus read_coils calls."""

    mock_pb = mock.MagicMock()
    with mock.patch(
        "homeassistant.components.modbus.modbus.ModbusTcpClient", return_value=mock_pb
    ):
        modbus_hub.setup()

        data = [0x15]
        mock_pb.read_discrete_inputs.return_value = ReadResult(data)
        result = modbus_hub.read_discrete_inputs(None, 17, 1)
        assert result.registers == data

        data = [0x15, 0x16]
        mock_pb.read_discrete_inputs.return_value = ReadResult(data)
        result = modbus_hub.read_discrete_inputs(None, 17, 2)
        assert result.registers == data

        data = [0x15, 0x16]
        mock_pb.read_discrete_inputs.side_effect = ModbusException("fail read_coils")
        result = modbus_hub.read_discrete_inputs(None, 17, 2)
        assert result is None


async def test_pb_read_input_registers(hass, modbus_hub):
    """Run test for pymodbus read_input_registers calls."""

    mock_pb = mock.MagicMock()
    with mock.patch(
        "homeassistant.components.modbus.modbus.ModbusTcpClient", return_value=mock_pb
    ):
        modbus_hub.setup()

        data = [0x15]
        mock_pb.read_input_registers.return_value = ReadResult(data)
        result = modbus_hub.read_input_registers(None, 17, 1)
        assert result.registers == data

        data = [0x15, 0x16]
        mock_pb.read_input_registers.return_value = ReadResult(data)
        result = modbus_hub.read_input_registers(None, 17, 2)
        assert result.registers == data

        data = [0x15, 0x16]
        mock_pb.read_input_registers.side_effect = ModbusException("fail read_coils")
        result = modbus_hub.read_input_registers(None, 17, 2)
        assert result is None


async def test_pb_read_holding_registers(hass, modbus_hub):
    """Run test for pymodbus read_holding_registers calls."""

    mock_pb = mock.MagicMock()
    with mock.patch(
        "homeassistant.components.modbus.modbus.ModbusTcpClient", return_value=mock_pb
    ):
        modbus_hub.setup()

        data = [0x15]
        mock_pb.read_holding_registers.return_value = ReadResult(data)
        result = modbus_hub.read_holding_registers(None, 17, 1)
        assert result.registers == data

        data = [0x15, 0x16]
        mock_pb.read_holding_registers.return_value = ReadResult(data)
        result = modbus_hub.read_holding_registers(None, 17, 2)
        assert result.registers == data

        data = [0x15, 0x16]
        mock_pb.read_holding_registers.side_effect = ModbusException("fail read_coils")
        result = modbus_hub.read_holding_registers(None, 17, 2)
        assert result is None


async def test_pb_service_write_register(hass):
    """Run test for service write_register."""

    conf_name = "myModbus"
    config = {
        DOMAIN: [
            {
                CONF_TYPE: "tcp",
                CONF_HOST: "modbusTestHost",
                CONF_PORT: 5501,
                CONF_NAME: conf_name,
            }
        ]
    }

    mock_pb = mock.MagicMock()
    with mock.patch(
        "homeassistant.components.modbus.modbus.ModbusTcpClient", return_value=mock_pb
    ):
        assert await async_setup_component(hass, DOMAIN, config) is True
        await hass.async_block_till_done()

        data = {ATTR_HUB: conf_name, ATTR_UNIT: 17, ATTR_ADDRESS: 16, ATTR_VALUE: 15}
        await hass.services.async_call(
            DOMAIN, SERVICE_WRITE_REGISTER, data, blocking=True
        )
        assert mock_pb.write_register.called
        assert mock_pb.write_register.call_args[0] == (
            data[ATTR_ADDRESS],
            data[ATTR_VALUE],
        )

        mock_pb.write_registers.side_effect = ModbusException("fail write_")
        await hass.services.async_call(
            DOMAIN, SERVICE_WRITE_REGISTER, data, blocking=True
        )

        data[ATTR_VALUE] = [1, 2, 3]
        await hass.services.async_call(
            DOMAIN, SERVICE_WRITE_REGISTER, data, blocking=True
        )
        assert mock_pb.write_registers.called
        assert mock_pb.write_registers.call_args[0] == (
            data[ATTR_ADDRESS],
            data[ATTR_VALUE],
        )


async def test_pb_service_write_coil(hass):
    """Run test for service write_coil."""

    conf_name = "myModbus"
    config = {
        DOMAIN: [
            {
                CONF_TYPE: "tcp",
                CONF_HOST: "modbusTestHost",
                CONF_PORT: 5501,
                CONF_NAME: conf_name,
            }
        ]
    }

    mock_pb = mock.MagicMock()
    with mock.patch(
        "homeassistant.components.modbus.modbus.ModbusTcpClient", return_value=mock_pb
    ):
        assert await async_setup_component(hass, DOMAIN, config) is True
        await hass.async_block_till_done()

        data = {ATTR_HUB: conf_name, ATTR_UNIT: 17, ATTR_ADDRESS: 16, ATTR_STATE: False}
        await hass.services.async_call(DOMAIN, SERVICE_WRITE_COIL, data, blocking=True)
        assert mock_pb.write_coil.called
        assert mock_pb.write_coil.call_args[0] == (
            data[ATTR_ADDRESS],
            data[ATTR_STATE],
        )

        mock_pb.write_registers.side_effect = ModbusException("fail write_")
        await hass.services.async_call(DOMAIN, SERVICE_WRITE_COIL, data, blocking=True)

        data[ATTR_STATE] = [True, False, True]
        await hass.services.async_call(DOMAIN, SERVICE_WRITE_COIL, data, blocking=True)
        assert mock_pb.write_coils.called
        assert mock_pb.write_coils.call_args[0] == (
            data[ATTR_ADDRESS],
            data[ATTR_STATE],
        )
