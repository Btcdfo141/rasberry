"""Constants for the Risco integration."""

from homeassistant.const import (
    CONF_SCAN_INTERVAL,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
)

DOMAIN = "risco"

RISCO_EVENT = "risco_event"

DATA_COORDINATOR = "risco"
EVENTS_COORDINATOR = "risco_events"

DEFAULT_SCAN_INTERVAL = 30

TYPE_LOCAL = "local"

MAX_COMMUNICATION_DELAY = 3

SYSTEM_UPDATE_SIGNAL = "risco_system_update"
CONF_CODE_ARM_REQUIRED = "code_arm_required"
CONF_CODE_DISARM_REQUIRED = "code_disarm_required"
CONF_RISCO_STATES_TO_HA = "risco_states_to_ha"
CONF_HA_STATES_TO_RISCO = "ha_states_to_risco"
CONF_COMMUNICATION_DELAY = "communication_delay"

RISCO_GROUPS = ["A", "B", "C", "D"]
RISCO_ARM = "arm"
RISCO_PARTIAL_ARM = "partial_arm"
RISCO_STATES = [RISCO_ARM, RISCO_PARTIAL_ARM, *RISCO_GROUPS]

DEFAULT_RISCO_GROUPS_TO_HA = {group: STATE_ALARM_ARMED_HOME for group in RISCO_GROUPS}
DEFAULT_RISCO_STATES_TO_HA = {
    RISCO_ARM: STATE_ALARM_ARMED_AWAY,
    RISCO_PARTIAL_ARM: STATE_ALARM_ARMED_HOME,
    **DEFAULT_RISCO_GROUPS_TO_HA,
}

DEFAULT_HA_STATES_TO_RISCO = {
    STATE_ALARM_ARMED_AWAY: RISCO_ARM,
    STATE_ALARM_ARMED_HOME: RISCO_PARTIAL_ARM,
}

DEFAULT_OPTIONS = {
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    CONF_CODE_ARM_REQUIRED: False,
    CONF_CODE_DISARM_REQUIRED: False,
    CONF_RISCO_STATES_TO_HA: DEFAULT_RISCO_STATES_TO_HA,
    CONF_HA_STATES_TO_RISCO: DEFAULT_HA_STATES_TO_RISCO,
}
