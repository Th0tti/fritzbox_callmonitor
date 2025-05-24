"""Sensor-Definitionen für Anruflisten und Voicemails."""
from __future__ import annotations
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity

from .base import FritzboxCallUpdateCoordinator
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: FritzboxCallUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[Entity] = [
        SensorOutgoingCalls(coordinator),
        SensorIncomingCalls(coordinator),
        SensorMissedCalls(coordinator),
    ]
    if coordinator.fetch_voicemails:
        entities.append(SensorVoicemails(coordinator))
    async_add_entities(entities)

class FritzboxHistorySensor(Entity):
    def __init__(self, coordinator: FritzboxCallUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_extra_state_attributes: dict = {}
        self._attr_should_poll = False

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self._handle_coordinator_update)
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self):
        self._update_state()
        self.async_write_ha_state()

    def _update_state(self):
        raise NotImplementedError

class SensorOutgoingCalls(FritzboxHistorySensor):
    _attr_unique_id = f"{DOMAIN}_outgoing_calls"
    _attr_name = "Abgehende Anrufe"
    _attr_icon = "mdi:phone-outgoing"

    def _update_state(self):
        calls = [c for c in self.coordinator.data["calls"] if c["type"] == "outgoing"]
        self._attr_state = len(calls)
        self._attr_extra_state_attributes["calls"] = calls

class SensorIncomingCalls(FritzboxHistorySensor):
    _attr_unique_id = f"{DOMAIN}_incoming_calls"
    _attr_name = "Eingehende Anrufe"
    _attr_icon = "mdi:phone-incoming"

    def _update_state(self):
        calls = [c for c in self.coordinator.data["calls"] if c["type"] == "incoming"]
        self._attr_state = len(calls)
        self._attr_extra_state_attributes["calls"] = calls

class SensorMissedCalls(FritzboxHistorySensor):
    _attr_unique_id = f"{DOMAIN}_missed_calls"
    _attr_name = "Verpasste Anrufe"
    _attr_icon = "mdi:phone-missed"

    def _update_state(self):
        calls = [c for c in self.coordinator.data["calls"] if c["type"] == "missed"]
        self._attr_state = len(calls)
        self._attr_extra_state_attributes["calls"] = calls

class SensorVoicemails(FritzboxHistorySensor):
    _attr_unique_id = f"{DOMAIN}_voicemails"
    _attr_name = "Sprachnachrichten"
    _attr_icon = "mdi:voicemail"

    def _update_state(self):
        msgs = self.coordinator.data["voicemails"]
        self._attr_state = len(msgs)
        self._attr_extra_state_attributes["messages"] = msgs

