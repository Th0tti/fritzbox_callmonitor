# custom_components/fritzbox_anrufe/const.py

"""Constants for the fritzbox_anrufe integration."""

from enum import StrEnum
from typing import Final

from homeassistant.const import Platform


class FritzState(StrEnum):
    """Fritz!Box call states."""

    RING = "RING"
    CALL = "CALL"
    CONNECT = "CONNECT"
    DISCONNECT = "DISCONNECT"


ATTR_PREFIXES = "prefixes"

FRITZ_ATTR_NAME = "name"
FRITZ_ATTR_SERIAL_NUMBER = "Serial"

UNKNOWN_NAME = "unknown"
SERIAL_NUMBER = "serial_number"
REGEX_NUMBER = r"[^\d\+]"

CONF_PHONEBOOK = "phonebook"
CONF_PHONEBOOK_NAME = "phonebook_name"
CONF_PREFIXES = "prefixes"

DEFAULT_HOST = "169.254.1.1" 
DEFAULT_PORT = 1012
DEFAULT_USERNAME = "admin"
DEFAULT_PHONEBOOK = 0
DEFAULT_NAME = "Phone"

DOMAIN: Final = "fritzbox_anrufe"
MANUFACTURER: Final = "AVM"

PLATFORMS = [Platform.SENSOR]
