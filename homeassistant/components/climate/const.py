"""Proides the constants needed for component."""

ATTR_AUX_HEAT = 'aux_heat'
ATTR_AWAY_MODE = 'away_mode'
ATTR_CURRENT_HUMIDITY = 'current_humidity'
ATTR_CURRENT_TEMPERATURE = 'current_temperature'
ATTR_FAN_LIST = 'fan_list'
ATTR_FAN_MODE = 'fan_mode'
ATTR_HOLD_MODE = 'hold_mode'
ATTR_HUMIDITY = 'humidity'
ATTR_MAX_HUMIDITY = 'max_humidity'
ATTR_MAX_TEMP = 'max_temp'
ATTR_MIN_HUMIDITY = 'min_humidity'
ATTR_MIN_TEMP = 'min_temp'
ATTR_OPERATION_LIST = 'operation_list'
ATTR_OPERATION_MODE = 'operation_mode'
ATTR_SWING_LIST = 'swing_list'
ATTR_SWING_MODE = 'swing_mode'
ATTR_TARGET_TEMP_HIGH = 'target_temp_high'
ATTR_TARGET_TEMP_LOW = 'target_temp_low'
ATTR_TARGET_TEMP_STEP = 'target_temp_step'

DEFAULT_MIN_TEMP = 7
DEFAULT_MAX_TEMP = 35
DEFAULT_MIN_HUMITIDY = 30
DEFAULT_MAX_HUMIDITY = 99

DOMAIN = 'climate'

SERVICE_SET_AUX_HEAT = 'set_aux_heat'
SERVICE_SET_AWAY_MODE = 'set_away_mode'
SERVICE_SET_FAN_MODE = 'set_fan_mode'
SERVICE_SET_HOLD_MODE = 'set_hold_mode'
SERVICE_SET_HUMIDITY = 'set_humidity'
SERVICE_SET_OPERATION_MODE = 'set_operation_mode'
SERVICE_SET_SWING_MODE = 'set_swing_mode'
SERVICE_SET_TEMPERATURE = 'set_temperature'

STATE_HEAT = 'heat'
STATE_COOL = 'cool'
STATE_IDLE = 'idle'
STATE_AUTO = 'auto'
STATE_MANUAL = 'manual'
STATE_DRY = 'dry'
STATE_FAN_ONLY = 'fan_only'
STATE_ECO = 'eco'

SUPPORT_TARGET_TEMPERATURE = 1
SUPPORT_TARGET_TEMPERATURE_HIGH = 2
SUPPORT_TARGET_TEMPERATURE_LOW = 4
SUPPORT_TARGET_HUMIDITY = 8
SUPPORT_TARGET_HUMIDITY_HIGH = 16
SUPPORT_TARGET_HUMIDITY_LOW = 32
SUPPORT_FAN_MODE = 64
SUPPORT_OPERATION_MODE = 128
SUPPORT_HOLD_MODE = 256
SUPPORT_SWING_MODE = 512
SUPPORT_AWAY_MODE = 1024
SUPPORT_AUX_HEAT = 2048
SUPPORT_ON_OFF = 4096
