from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class FritzboxCallMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Fritz!Box Callmonitor", data=user_input)
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host"): str,
                vol.Optional("username", default=""): str,
                vol.Required("password"): str,
            })
        )
