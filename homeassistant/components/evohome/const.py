"""Provides the constants needed for evohome."""

DOMAIN = 'evohome'

STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN

# The Parent's (i.e. TCS, Controller's) operating mode is one of:
EVO_RESET = 'AutoWithReset'
EVO_AUTO = 'Auto'
EVO_AUTOECO = 'AutoWithEco'
EVO_AWAY = 'Away'
EVO_DAYOFF = 'DayOff'
EVO_CUSTOM = 'Custom'
EVO_HEATOFF = 'HeatingOff'

# The Childs' operating mode is one of:
EVO_FOLLOW = 'FollowSchedule'  # the operating mode is 'inherited' from the TCS
EVO_TEMPOVER = 'TemporaryOverride'
EVO_PERMOVER = 'PermanentOverride'

# These are used only to help prevent E501 (line too long) violations
GWS = 'gateways'
TCS = 'temperatureControlSystems'
