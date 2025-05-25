"""Constants for the fritzbox_anrufe integration."""

DOMAIN = "fritzbox_anrufe"

CONF_PHONEBOOK = "phonebook"
CONF_PREFIXES = "prefixes"

DEFAULT_PREFIXES = []

SENSOR_TYPE_CALL_MONITOR = "call_monitor"
SENSOR_DEVICE_CLASS = "enum"
SENSOR_NAME_FORMAT = "Fritz!Box Anrufe {phonebook_id}"

STATE_RINGING = "ringing"
STATE_DIALING = "dialing"
STATE_TALKING = "talking"
STATE_IDLE = "idle"

ATTR_TYPE = "type"
ATTR_FROM = "from"
ATTR_TO = "to"
ATTR_WITH = "with"
ATTR_DEVICE = "device"
ATTR_INITIATED = "initiated"
ATTR_ACCEPTED = "accepted"
ATTR_CLOSED = "closed"
ATTR_DURATION = "duration"
ATTR_FROM_NAME = "from_name"
ATTR_WITH_NAME = "with_name"
ATTR_TO_NAME = "to_name"
ATTR_VIP = "vip"
ATTR_PREFIXES = "prefixes"
