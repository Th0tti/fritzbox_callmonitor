"""Fritz!Box Anrufe Integration."""
from __future__ import annotations
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .base import FritzboxCallUpdateCoordinator
from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_TR064_PORT,
    CONF_MONITOR_PORT,
    CONF_FETCH_CALL_HISTORY,
    CONF_FETCH_VOICEMAILS,
    DEFAULT_TR064_PORT,
    DEFAULT_MONITOR_PORT,
    DEFAULT_UPDATE_INTERVAL,
)
from .sensor import FritzBoxCallSensor

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    data = entry.data
    host = data[CONF_HOST]
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]
    tr064_port = data.get(CONF_TR064_PORT, DEFAULT_TR064_PORT)
    monitor_port = data.get(CONF_MONITOR_PORT, DEFAULT_MONITOR_PORT)
    fetch_call_history = data.get(CONF_FETCH_CALL_HISTORY, True)
    fetch_voicemails = data.get(CONF_FETCH_VOICEMAILS, False)

    coordinator = FritzboxCallUpdateCoordinator(
        hass,
        host=host,
        username=username,
        password=password,
        tr064_port=tr064_port,
        monitor_port=monitor_port,
        fetch_call_history=fetch_call_history,
        fetch_voicemails=fetch_voicemails,
        update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
