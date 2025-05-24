"""Sensor-Definitionen für Call-History, Voicemails und letzten Anruf."""
from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity

from .base import FritzboxCallUpdateCoordinator
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Registriere alle Sensor-Entitäten."""
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
    """Basis-Klasse für unsere Sensors, die über den Coordinator updaten."""

    def __init__(self, coordinator: FritzboxCallUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_extra_state_attributes: dict = {}
        self._attr_should_poll = False

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self._handle_coordinator_update)
        # gleich initial einen Zustand schreiben
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self):
        self._update_state()
        self.async_write_ha_state()

    def _update_state(self):
        raise NotImplementedError


class SensorCallMonitor(FritzboxHistorySensor):
    """Core-Entität: Ausgabe des letzten Anruf-Events."""
    _attr_unique_id = f"{DOMAIN}_last_call"
    _attr_name = "Letzter Anruf"
    _attr_icon = "mdi:phone"

    def _update_state(self):
        calls = self.coordinator.data["calls"]
        if calls:
            last = calls[-1]
            self._attr_state = last["type"]
            self._attr_extra_state_attributes = {
                "number": last["number"],
                "weekday": last["weekday"],
                "date": last["date"],
                "time": last["time"],
                "duration_seconds": last["duration"],
            }
        else:
            self._attr_state = "idle"
            self._attr_extra_state_attributes = {}


class SensorOutgoingCalls(FritzboxHistorySensor):
    _attr_unique_id = f"{DOMAIN}_outgoing_calls"
    _attr_name = "Abgehende Anrufe"
    _attr_icon = "mdi:phone-outgoing"

    def _update_state(self):
        calls = [c for c in self.coordinator.data["calls"] if c["type"] == "outgoing"]
        self._attr_state = len(calls)
        self._attr_extra_state_attributes = {"calls": calls}


class SensorIncomingCalls(FritzboxHistorySensor):
    _attr_unique_id = f"{DOMAIN}_incoming_calls"
    _attr_name = "Eingehende Anrufe"
    _attr_icon = "mdi:phone-incoming"

    def _update_state(self):
        calls = [c for c in self.coordinator.data["calls"] if c["type"] == "incoming"]
        self._attr_state = len(calls)
        self._attr_extra_state_attributes = {"calls": calls}


class SensorMissedCalls(FritzboxHistorySensor):
    _attr_unique_id = f"{DOMAIN}_missed_calls"
    _attr_name = "Verpasste Anrufe"
    _attr_icon = "mdi:phone-missed"

    def _update_state(self):
        calls = [c for c in self.coordinator.data["calls"] if c["type"] == "missed"]
        self._attr_state = len(calls)
        self._attr_extra_state_attributes = {"calls": calls}


class SensorVoicemails(FritzboxHistorySensor):
    _attr_unique_id = f"{DOMAIN}_voicemails"
    _attr_name = "Sprachnachrichten"
    _attr_icon = "mdi:voicemail"

    def _update_state(self):
        msgs = self.coordinator.data["voicemails"]
        self._attr_state = len(msgs)
        self._attr_extra_state_attributes = {"messages": msgs}
