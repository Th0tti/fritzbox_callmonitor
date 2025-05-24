"""Sensor-Definitionen für Live-Core, History und Voicemails."""
from __future__ import annotations

from datetime import datetime
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity

from .base import FritzboxCallUpdateCoordinator
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Registriere Core- und History-Sensoren."""
    coordinator: FritzboxCallUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[Entity] = [
        SensorCallMonitor(coordinator),
        SensorOutgoingCalls(coordinator),
        SensorIncomingCalls(coordinator),
        SensorMissedCalls(coordinator),
    ]
    if coordinator.fetch_voicemails:
        entities.append(SensorVoicemails(coordinator))

    async_add_entities(entities)

class FritzboxHistorySensor(Entity):
    """Basis-Klasse ohne Polling, mit UpdateListener."""

    def __init__(self, coordinator: FritzboxCallUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_extra_state_attributes: dict = {}
        self._attr_should_poll = False

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self._handle_coordinator_update)
        # sofort initial beschreiben
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self):
        self._update_state()
        self.async_write_ha_state()

    def _update_state(self):
        raise NotImplementedError

class SensorCallMonitor(FritzboxHistorySensor):
    """Core: Zeigt den letzten Anruf-Status und Attribute."""
    _attr_unique_id = f"{DOMAIN}_last_call"
    _attr_name = "Letzter Anruf"
    _attr_icon = "mdi:phone"

    def _update_state(self):
        calls = self.coordinator.data.get("calls", [])
        if not calls:
            self._attr_state = "idle"
            self._attr_extra_state_attributes = {}
            return

        # nach datetime absteigend sortieren
        last = sorted(calls, key=lambda c: c["datetime"], reverse=True)[0]
        self._attr_state = last["type"]
        self._attr_extra_state_attributes = {
            "number": last["number"],
            "weekday": last["weekday"],
            "date": last["date"],
            "time": last["time"],
            "duration_seconds": last["duration"],
        }

class SensorOutgoingCalls(FritzboxHistorySensor):
    """Anzahl der abgehenden Anrufe + History als Attribute."""
    _attr_unique_id = f"{DOMAIN}_outgoing_calls"
    _attr_name = "Abgehende Anrufe"
    _attr_icon = "mdi:phone-outgoing"

    def _update_state(self):
        calls = [c for c in self.coordinator.data.get("calls", []) if c["type"] == "outgoing"]
        self._attr_state = len(calls)
        self._attr_extra_state_attributes = {"calls": calls}

class SensorIncomingCalls(FritzboxHistorySensor):
    _attr_unique_id = f"{DOMAIN}_incoming_calls"
    _attr_name = "Eingehende Anrufe"
    _attr_icon = "mdi:phone-incoming"

    def _update_state(self):
        calls = [c for c in self.coordinator.data.get("calls", []) if c["type"] == "incoming"]
        self._attr_state = len(calls)
        self._attr_extra_state_attributes = {"calls": calls}

class SensorMissedCalls(FritzboxHistorySensor):
    _attr_unique_id = f"{DOMAIN}_missed_calls"
    _attr_name = "Verpasste Anrufe"
    _attr_icon = "mdi:phone-missed"

    def _update_state(self):
        calls = [c for c in self.coordinator.data.get("calls", []) if c["type"] == "missed"]
        self._attr_state = len(calls)
        self._attr_extra_state_attributes = {"calls": calls}

class SensorVoicemails(FritzboxHistorySensor):
    _attr_unique_id = f"{DOMAIN}_voicemails"
    _attr_name = "Sprachnachrichten"
    _attr_icon = "mdi:voicemail"

    def _update_state(self):
        msgs = self.coordinator.data.get("voicemails", [])
        self._attr_state = len(msgs)
        self._attr_extra_state_attributes = {"messages": msgs}
