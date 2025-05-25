"""The fritzbox_anrufe integration."""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import DOMAIN
from .base import FritzBoxBase

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the fritzbox_anrufe component (legacy)."""
    _LOGGER.debug("Setting up fritzbox_anrufe")
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up fritzbox_anrufe from a config entry."""
    _LOGGER.debug("Loading config entry %s", entry.entry_id)
    fritz = FritzBoxBase(hass, entry.data)
    hass.data[DOMAIN][entry.entry_id] = fritz

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.debug("Unloading config entry %s", entry.entry_id)
    unload_ok = all(
        await hass.config_entries.async_forward_entry_unload(entry, platform)
        for platform in PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
