"""Constants for the Bluetooth integration."""

DOMAIN = "bluetooth"
DEFAULT_NAME = "Bluetooth"

CONF_ADAPTER = "adapter"

MACOS_DEFAULT_BLUETOOTH_ADAPTER = "CoreBluetooth"
LINUX_DEFAULT_BLUETOOTH_ADAPTER = "hci0"

DEFAULT_ADAPTERS = {MACOS_DEFAULT_BLUETOOTH_ADAPTER, LINUX_DEFAULT_BLUETOOTH_ADAPTER}
