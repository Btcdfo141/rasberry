"""Constants for the Xiaomi Miio component."""
DOMAIN = "xiaomi_miio"

# Config flow
CONF_FLOW_TYPE = "config_flow_device"
CONF_GATEWAY = "gateway"
CONF_DEVICE = "device"
CONF_MODEL = "model"
CONF_MAC = "mac"
CONF_CLOUD_USERNAME = "cloud_username"
CONF_CLOUD_PASSWORD = "cloud_password"
CONF_CLOUD_COUNTRY = "cloud_country"
CONF_MANUAL = "manual"

# Options flow
CONF_CLOUD_SUBDEVICES = "cloud_subdevices"

# Keys
KEY_COORDINATOR = "coordinator"
KEY_DEVICE = "device"

# Attributes
ATTR_AVAILABLE = "available"

# Status
SUCCESS = ["ok"]

# Cloud
SERVER_COUNTRY_CODES = ["cn", "de", "i2", "ru", "sg", "us"]
DEFAULT_CLOUD_COUNTRY = "cn"

# Fan Models
MODEL_AIRPURIFIER_V1 = "zhimi.airpurifier.v1"
MODEL_AIRPURIFIER_V2 = "zhimi.airpurifier.v2"
MODEL_AIRPURIFIER_V3 = "zhimi.airpurifier.v3"
MODEL_AIRPURIFIER_V5 = "zhimi.airpurifier.v5"
MODEL_AIRPURIFIER_PRO = "zhimi.airpurifier.v6"
MODEL_AIRPURIFIER_PRO_V7 = "zhimi.airpurifier.v7"
MODEL_AIRPURIFIER_M1 = "zhimi.airpurifier.m1"
MODEL_AIRPURIFIER_M2 = "zhimi.airpurifier.m2"
MODEL_AIRPURIFIER_MA1 = "zhimi.airpurifier.ma1"
MODEL_AIRPURIFIER_MA2 = "zhimi.airpurifier.ma2"
MODEL_AIRPURIFIER_SA1 = "zhimi.airpurifier.sa1"
MODEL_AIRPURIFIER_SA2 = "zhimi.airpurifier.sa2"
MODEL_AIRPURIFIER_2S = "zhimi.airpurifier.mc1"
MODEL_AIRPURIFIER_2H = "zhimi.airpurifier.mc2"
MODEL_AIRPURIFIER_3 = "zhimi.airpurifier.ma4"
MODEL_AIRPURIFIER_3H = "zhimi.airpurifier.mb3"
MODEL_AIRPURIFIER_PROH = "zhimi.airpurifier.va1"

MODEL_AIRHUMIDIFIER_V1 = "zhimi.humidifier.v1"
MODEL_AIRHUMIDIFIER_CA1 = "zhimi.humidifier.ca1"
MODEL_AIRHUMIDIFIER_CA4 = "zhimi.humidifier.ca4"
MODEL_AIRHUMIDIFIER_CB1 = "zhimi.humidifier.cb1"
MODEL_AIRHUMIDIFIER_JSQ = "deerma.humidifier.jsq"
MODEL_AIRHUMIDIFIER_JSQ1 = "deerma.humidifier.jsq1"
MODEL_AIRHUMIDIFIER_MJJSQ = "deerma.humidifier.mjjsq"

MODEL_AIRFRESH_VA2 = "zhimi.airfresh.va2"

MODEL_FAN_P5 = "dmaker.fan.p5"

MODELS_FAN_MIIO = [MODEL_FAN_P5]

MODELS_PURIFIER_MIOT = [
    MODEL_AIRPURIFIER_3,
    MODEL_AIRPURIFIER_3H,
    MODEL_AIRPURIFIER_PROH,
]
MODELS_PURIFIER_MIIO = [
    MODEL_AIRPURIFIER_V1,
    MODEL_AIRPURIFIER_V2,
    MODEL_AIRPURIFIER_V3,
    MODEL_AIRPURIFIER_V5,
    MODEL_AIRPURIFIER_PRO,
    MODEL_AIRPURIFIER_PRO_V7,
    MODEL_AIRPURIFIER_M1,
    MODEL_AIRPURIFIER_M2,
    MODEL_AIRPURIFIER_MA1,
    MODEL_AIRPURIFIER_MA2,
    MODEL_AIRPURIFIER_SA1,
    MODEL_AIRPURIFIER_SA2,
    MODEL_AIRPURIFIER_2S,
    MODEL_AIRPURIFIER_2H,
    MODEL_AIRFRESH_VA2,
]
MODELS_HUMIDIFIER_MIIO = [
    MODEL_AIRHUMIDIFIER_V1,
    MODEL_AIRHUMIDIFIER_CA1,
    MODEL_AIRHUMIDIFIER_CB1,
]
MODELS_HUMIDIFIER_MIOT = [MODEL_AIRHUMIDIFIER_CA4]
MODELS_HUMIDIFIER_MJJSQ = [
    MODEL_AIRHUMIDIFIER_JSQ,
    MODEL_AIRHUMIDIFIER_JSQ1,
    MODEL_AIRHUMIDIFIER_MJJSQ,
]

# AirQuality Models
MODEL_AIRQUALITYMONITOR_V1 = "zhimi.airmonitor.v1"
MODEL_AIRQUALITYMONITOR_B1 = "cgllc.airmonitor.b1"
MODEL_AIRQUALITYMONITOR_S1 = "cgllc.airmonitor.s1"
MODEL_AIRQUALITYMONITOR_CGDN1 = "cgllc.airm.cgdn1"

# Light Models
MODELS_LIGHT_EYECARE = ["philips.light.sread1"]
MODELS_LIGHT_CEILING = ["philips.light.ceiling", "philips.light.zyceiling"]
MODELS_LIGHT_MOON = ["philips.light.moonlight"]
MODELS_LIGHT_BULB = [
    "philips.light.bulb",
    "philips.light.candle",
    "philips.light.candle2",
    "philips.light.downlight",
]
MODELS_LIGHT_MONO = ["philips.light.mono1"]

# Model lists
MODELS_GATEWAY = ["lumi.gateway", "lumi.acpartner"]
MODELS_SWITCH = [
    "chuangmi.plug.v1",
    "chuangmi.plug.v3",
    "chuangmi.plug.hmi208",
    "qmi.powerstrip.v1",
    "zimi.powerstrip.v2",
    "chuangmi.plug.m1",
    "chuangmi.plug.m3",
    "chuangmi.plug.v2",
    "chuangmi.plug.hmi205",
    "chuangmi.plug.hmi206",
]
MODELS_FAN = MODELS_PURIFIER_MIIO + MODELS_PURIFIER_MIOT + MODELS_FAN_MIIO
MODELS_HUMIDIFIER = (
    MODELS_HUMIDIFIER_MIOT + MODELS_HUMIDIFIER_MIIO + MODELS_HUMIDIFIER_MJJSQ
)
MODELS_LIGHT = (
    MODELS_LIGHT_EYECARE
    + MODELS_LIGHT_CEILING
    + MODELS_LIGHT_MOON
    + MODELS_LIGHT_BULB
    + MODELS_LIGHT_MONO
)
MODELS_VACUUM = ["roborock.vacuum", "rockrobo.vacuum"]
MODELS_AIR_MONITOR = [
    MODEL_AIRQUALITYMONITOR_V1,
    MODEL_AIRQUALITYMONITOR_B1,
    MODEL_AIRQUALITYMONITOR_S1,
    MODEL_AIRQUALITYMONITOR_CGDN1,
]

MODELS_ALL_DEVICES = (
    MODELS_SWITCH
    + MODELS_VACUUM
    + MODELS_AIR_MONITOR
    + MODELS_FAN
    + MODELS_HUMIDIFIER
    + MODELS_LIGHT
)
MODELS_ALL = MODELS_ALL_DEVICES + MODELS_GATEWAY

# Fan/Humidifier Services
SERVICE_SET_FAVORITE_LEVEL = "fan_set_favorite_level"
SERVICE_SET_FAN_LEVEL = "fan_set_fan_level"
SERVICE_SET_VOLUME = "fan_set_volume"
SERVICE_RESET_FILTER = "fan_reset_filter"
SERVICE_SET_EXTRA_FEATURES = "fan_set_extra_features"
SERVICE_SET_DRY = "set_dry"
SERVICE_SET_MOTOR_SPEED = "fan_set_motor_speed"

# Light Services
SERVICE_SET_SCENE = "light_set_scene"
SERVICE_SET_DELAYED_TURN_OFF = "light_set_delayed_turn_off"
SERVICE_REMINDER_ON = "light_reminder_on"
SERVICE_REMINDER_OFF = "light_reminder_off"
SERVICE_NIGHT_LIGHT_MODE_ON = "light_night_light_mode_on"
SERVICE_NIGHT_LIGHT_MODE_OFF = "light_night_light_mode_off"
SERVICE_EYECARE_MODE_ON = "light_eyecare_mode_on"
SERVICE_EYECARE_MODE_OFF = "light_eyecare_mode_off"

# Remote Services
SERVICE_LEARN = "remote_learn_command"
SERVICE_SET_REMOTE_LED_ON = "remote_set_led_on"
SERVICE_SET_REMOTE_LED_OFF = "remote_set_led_off"

# Switch Services
SERVICE_SET_WIFI_LED_ON = "switch_set_wifi_led_on"
SERVICE_SET_WIFI_LED_OFF = "switch_set_wifi_led_off"
SERVICE_SET_POWER_MODE = "switch_set_power_mode"
SERVICE_SET_POWER_PRICE = "switch_set_power_price"

# Vacuum Services
SERVICE_MOVE_REMOTE_CONTROL = "vacuum_remote_control_move"
SERVICE_MOVE_REMOTE_CONTROL_STEP = "vacuum_remote_control_move_step"
SERVICE_START_REMOTE_CONTROL = "vacuum_remote_control_start"
SERVICE_STOP_REMOTE_CONTROL = "vacuum_remote_control_stop"
SERVICE_CLEAN_SEGMENT = "vacuum_clean_segment"
SERVICE_CLEAN_ZONE = "vacuum_clean_zone"
SERVICE_GOTO = "vacuum_goto"

# Features
FEATURE_SET_BUZZER = 1
FEATURE_SET_LED = 2
FEATURE_SET_CHILD_LOCK = 4
FEATURE_SET_LED_BRIGHTNESS = 8
FEATURE_SET_FAVORITE_LEVEL = 16
FEATURE_SET_AUTO_DETECT = 32
FEATURE_SET_LEARN_MODE = 64
FEATURE_SET_VOLUME = 128
FEATURE_RESET_FILTER = 256
FEATURE_SET_EXTRA_FEATURES = 512
FEATURE_SET_TARGET_HUMIDITY = 1024
FEATURE_SET_DRY = 2048
FEATURE_SET_FAN_LEVEL = 4096
FEATURE_SET_MOTOR_SPEED = 8192
FEATURE_SET_CLEAN = 16384
FEATURE_SET_NATURAL_MODE = 32768
FEATURE_SET_OSCILLATION_ANGLE = 65536

FEATURE_FLAGS_AIRPURIFIER_MIIO = (
    FEATURE_SET_BUZZER
    | FEATURE_SET_CHILD_LOCK
    | FEATURE_SET_LED
    | FEATURE_SET_FAVORITE_LEVEL
    | FEATURE_SET_LEARN_MODE
    | FEATURE_RESET_FILTER
    | FEATURE_SET_EXTRA_FEATURES
)

FEATURE_FLAGS_AIRPURIFIER_MIOT = (
    FEATURE_SET_BUZZER
    | FEATURE_SET_CHILD_LOCK
    | FEATURE_SET_FAVORITE_LEVEL
    | FEATURE_SET_FAN_LEVEL
    | FEATURE_SET_LED_BRIGHTNESS
)

FEATURE_FLAGS_AIRPURIFIER_PRO = (
    FEATURE_SET_CHILD_LOCK
    | FEATURE_SET_LED
    | FEATURE_SET_FAVORITE_LEVEL
    | FEATURE_SET_VOLUME
)

FEATURE_FLAGS_AIRPURIFIER_PRO_V7 = (
    FEATURE_SET_CHILD_LOCK
    | FEATURE_SET_LED
    | FEATURE_SET_FAVORITE_LEVEL
    | FEATURE_SET_VOLUME
)

FEATURE_FLAGS_AIRPURIFIER_2S = (
    FEATURE_SET_BUZZER
    | FEATURE_SET_CHILD_LOCK
    | FEATURE_SET_LED
    | FEATURE_SET_FAVORITE_LEVEL
)

FEATURE_FLAGS_AIRPURIFIER_V1 = FEATURE_FLAGS_AIRPURIFIER_MIIO | FEATURE_SET_AUTO_DETECT

FEATURE_FLAGS_AIRPURIFIER_V3 = (
    FEATURE_SET_BUZZER | FEATURE_SET_CHILD_LOCK | FEATURE_SET_LED
)

FEATURE_FLAGS_AIRHUMIDIFIER = (
    FEATURE_SET_BUZZER | FEATURE_SET_CHILD_LOCK | FEATURE_SET_TARGET_HUMIDITY
)

FEATURE_FLAGS_AIRHUMIDIFIER_CA_AND_CB = FEATURE_FLAGS_AIRHUMIDIFIER | FEATURE_SET_DRY

FEATURE_FLAGS_AIRHUMIDIFIER_MJSSQ = (
    FEATURE_SET_BUZZER | FEATURE_SET_LED | FEATURE_SET_TARGET_HUMIDITY
)

FEATURE_FLAGS_AIRHUMIDIFIER_CA4 = (
    FEATURE_SET_BUZZER
    | FEATURE_SET_CHILD_LOCK
    | FEATURE_SET_TARGET_HUMIDITY
    | FEATURE_SET_DRY
    | FEATURE_SET_MOTOR_SPEED
    | FEATURE_SET_CLEAN
)

FEATURE_FLAGS_AIRFRESH = (
    FEATURE_SET_BUZZER
    | FEATURE_SET_CHILD_LOCK
    | FEATURE_SET_LED
    | FEATURE_SET_LED_BRIGHTNESS
    | FEATURE_RESET_FILTER
    | FEATURE_SET_EXTRA_FEATURES
)

FEATURE_FLAGS_FAN_P5 = (
    FEATURE_SET_BUZZER
    | FEATURE_SET_CHILD_LOCK
    | FEATURE_SET_NATURAL_MODE
    | FEATURE_SET_OSCILLATION_ANGLE
    | FEATURE_SET_LED
)
