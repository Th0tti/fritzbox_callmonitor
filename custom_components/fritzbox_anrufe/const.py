"""Konstanten für die Fritz!Box Anrufe Integration."""
DOMAIN = "fritzbox_anrufe"

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_TR064_PORT = "tr064_port"
CONF_MONITOR_PORT = "monitor_port"
CONF_FETCH_CALL_HISTORY = "fetch_call_history"
CONF_FETCH_VOICEMAILS = "fetch_voicemails"

DEFAULT_TR064_PORT = 49000
DEFAULT_MONITOR_PORT = 1012
DEFAULT_UPDATE_INTERVAL = 3600  # Sekunden

# Für Phonebook
UNKNOWN_NAME = "unknown"
REGEX_NUMBER = r"[^\d\+]"
