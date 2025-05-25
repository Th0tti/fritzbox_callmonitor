"""Base class for Fritz!Box connection and call monitoring."""
import logging
from datetime import datetime

from fritzconnection import FritzConnection, FritzCall
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    CONF_PHONEBOOK,
    CONF_PREFIXES,
    SENSOR_TYPE_CALL_MONITOR,
    SENSOR_NAME_FORMAT,
)
_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = 1  # seconds

class FritzBoxBase:
    """Manage connection and polling for call monitor."""

    def __init__(self, hass, config):
        self.hass = hass
        self.host = config.get("host")
        self.port = config.get("port")
        self.username = config.get("username")
        self.password = config.get("password")
        self.phonebook = config.get(CONF_PHONEBOOK)
        self.prefixes = config.get(CONF_PREFIXES)
        self.fc = FritzConnection(address=self.host, port=self.port,
                                  user=self.username, password=self.password)
        self.fc.call_action = FritzCall(self.fc).call_action
        self._devices = {}

    async def async_setup(self):
        """Set up call monitor sensor."""
        await self.hass.loop.run_in_executor(None, self.fc.call_action, "NewCall")
        async_track_time_interval(self.hass, self._update, SCAN_INTERVAL)

    async def _update(self, now):
        """Poll and fire events for each new call state."""
        try:
            result = await self.hass.loop.run_in_executor(None, self.fc.call_action, "GetCallList")
        except Exception as err:
            _LOGGER.error("Error fetching call list: %s", err)
            return

        for call in result["CallList"]:
            phonebook_id = self.phonebook
            unique_id = f"{self.fc.system_call_action.sns.serial_number}-{phonebook_id}"
            self.hass.bus.async_fire(
                f"{DOMAIN}_{unique_id}", {"phonebook_id": phonebook_id, "call": call}
            )
