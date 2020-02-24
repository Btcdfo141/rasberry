"""Constants used by the Netatmo component."""
from datetime import timedelta

API = "api"

DOMAIN = "netatmo"
MANUFACTURER = "Netatmo"

AUTH = "netatmo_auth"
CONF_PUBLIC = "public_sensor_config"
CAMERA_DATA = "netatmo_camera"
HOME_DATA = "netatmo_home_data"

CONF_CLOUDHOOK_URL = "cloudhook_url"

OAUTH2_AUTHORIZE = "https://api.netatmo.com/oauth2/authorize"
OAUTH2_TOKEN = "https://api.netatmo.com/oauth2/token"

DATA_PERSONS = "netatmo_persons"

NETATMO_WEBHOOK_URL = None

DEFAULT_PERSON = "Unknown"
DEFAULT_DISCOVERY = True
DEFAULT_WEBHOOKS = False

EVENT_PERSON = "person"
EVENT_MOVEMENT = "movement"
EVENT_HUMAN = "human"
EVENT_ANIMAL = "animal"
EVENT_VEHICLE = "vehicle"
EVENT_OUTDOOR = "Outdoor"
EVENT_CONNECTION = "connection"
EVENT_HUSH = "hush"
EVENT_SMOKE = "smoke"
EVENT_TAMPERED = "tampered"
EVENT_OFF = "off"
EVENT_ON = "on"
EVENT_TAG_BIG_MOVE = "tag_big_move"
EVENT_TAG_SMALL_MOVE = "tag_small_move"
EVENT_TAG_OPEN = "tag_open"

EVENT_BUS_PERSON = "netatmo_person"
EVENT_BUS_MOVEMENT = "netatmo_movement"
EVENT_BUS_HUMAN = "netatmo_human"
EVENT_BUS_ANIMAL = "netatmo_animal"
EVENT_BUS_VEHICLE = "netatmo_vehicle"
EVENT_BUS_OUTDOOR = "netatmo_outdoor"
EVENT_BUS_OTHER = "netatmo_other"
EVENT_BUS_CONNECTION = "netatmo_connection"
EVENT_BUS_HUSH = "netatmo_hush"
EVENT_BUS_SMOKE = "netatmo_smoke"
EVENT_BUS_TAMPERED = "netatmo_tampered"
EVENT_BUS_OFF = "netatmo_off"
EVENT_BUS_ON = "netatmo_on"
EVENT_BUS_TAG_BIG_MOVE = "netatmo_tag_big_move"
EVENT_BUS_TAG_SMALL_MOVE = "netatmo_tag_small_move"
EVENT_BUS_TAG_OPEN = "netatmo_tag_open"

ATTR_ID = "id"
ATTR_PSEUDO = "pseudo"
ATTR_NAME = "name"
ATTR_EVENT_LIST = "event_list"
ATTR_EVENT_TYPE = "event_type"
ATTR_MESSAGE = "message"
ATTR_CAMERA_ID = "camera_id"
ATTR_HOME_ID = "home_id"
ATTR_HOME_NAME = "home_name"
ATTR_PERSONS = "persons"
ATTR_IS_KNOWN = "is_known"
ATTR_FACE_URL = "face_url"
ATTR_SNAPSHOT_URL = "snapshot_url"
ATTR_VIGNETTE_URL = "vignette_url"
ATTR_SCHEDULE_ID = "schedule_id"
ATTR_SCHEDULE_NAME = "schedule_name"

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)
MIN_TIME_BETWEEN_EVENT_UPDATES = timedelta(seconds=5)

SERVICE_SETSCHEDULE = "set_schedule"
