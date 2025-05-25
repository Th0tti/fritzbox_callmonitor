"""Config flow for fritzbox_anrufe integration."""
import logging

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD
import voluptuous as vol

from .const import DOMAIN, CONF_PHONEBOOK, CONF_PREFIXES, DEFAULT_PREFIXES

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=49000): int,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_PHONEBOOK, default=0): int,
        vol.Optional(CONF_PREFIXES, default=DEFAULT_PREFIXES): list,
    }
)

class FritzBoxAnrufeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for fritzbox_anrufe."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Hier könnte man Connectivity prüfen
            return self.async_create_entry(title=f"{user_input[CONF_HOST]}", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
