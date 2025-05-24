"""Fritz!Box Call Monitor integration."""
from __future__ import annotations
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .base import FritzboxCallUpdateCoordinator
from .const import (
    DOMAIN,
    CONF_FETCH_CALL_HISTORY,
    CONF_FETCH_VOICEMAILS,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PORT,
    DEFAULT_UPDATE_INTERVAL,
)
from .sensor import (
    SensorOutgoingCalls,
    SensorIncomingCalls,
    SensorMissedCalls,
    SensorVoicemails,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    port = entry.data.get(CONF_PORT)
    fetch_call_history = entry.data.get(CONF_FETCH_CALL_HISTORY)
    fetch_voicemails = entry.data.get(CONF_FETCH_VOICEMAILS)

    coordinator = FritzboxCallUpdateCoordinator(
        hass,
        host=host,
        username=username,
        password=password,
        port=port,
        fetch_call_history=fetch_call_history,
        fetch_voicemails=fetch_voicemails,
        update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
