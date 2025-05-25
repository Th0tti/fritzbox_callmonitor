"""Config Flow für Fritz!Box Anrufe."""
from __future__ import annotations
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD

from .const import (
    DOMAIN,
    DEFAULT_TR064_PORT,
    DEFAULT_MONITOR_PORT,
    CONF_TR064_PORT,
    CONF_MONITOR_PORT,
    CONF_FETCH_CALL_HISTORY,
    CONF_FETCH_VOICEMAILS,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_TR064_PORT, default=DEFAULT_TR064_PORT): int,
        vol.Optional(CONF_MONITOR_PORT, default=DEFAULT_MONITOR_PORT): int,
        vol.Optional(CONF_FETCH_CALL_HISTORY, default=True): bool,
        vol.Optional(CONF_FETCH_VOICEMAILS, default=False): bool,
    }
)

class FritzboxAnrufeFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle config flow of Fritzbox_Anrufe."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            return self.async_create_entry(title="Fritz!Box Anrufe", data=user_input)
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)
