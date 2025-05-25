"""Core-Sensor für den letzten Anruf mit ringing/dialing/talking/idle."""
from __future__ import annotations

import logging
import queue
from collections.abc import Mapping
from datetime import datetime, timedelta
from enum import StrEnum
from threading import Event as ThreadingEvent, Thread
from time import sleep
from typing import Any, cast

from fritzconnection.core.fritzmonitor import FritzMonitor

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_PHONEBOOK, CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .base import Contact, FritzBoxPhonebook
from .const import (
    ATTR_PREFIXES,
    DOMAIN,
    MANUFACTURER,
    SERIAL_NUMBER,
    FritzState,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=3)

class CallState(StrEnum):
    RINGING = "ringing"
    DIALING = "dialing"
    TALKING = "talking"
    IDLE = "idle"

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    fritzbox_pb: FritzBoxPhonebook = config_entry.runtime_data
    fritzbox_pb.init_phonebook()
    phonebook_id: int = config_entry.data[CONF_PHONEBOOK]
    prefixes = config_entry.options.get("prefixes")
    serial = config_entry.data[SERIAL_NUMBER]
    host = config_entry.data[CONF_HOST]
    port = config_entry.data[CONF_MONITOR_PORT]
    uid = f"{serial}-{phonebook_id}"
    sensor = FritzBoxCallSensor(
        phonebook_name=config_entry.title,
        unique_id=uid,
        fritzbox_phonebook=fritzbox_pb,
        prefixes=prefixes,
        host=host,
        port=port,
    )
    async_add_entities([sensor])

class FritzBoxCallSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = DOMAIN
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(CallState)

    def __init__(
        self,
        phonebook_name: str,
        unique_id: str,
        fritzbox_phonebook: FritzBoxPhonebook,
        prefixes: list[str] | None,
        host: str,
        port: int,
    ) -> None:
        self._fritzbox_phonebook = fritzbox_phonebook
        self._fritzbox_phonebook.prefixes = prefixes
        self._host = host
        self._port = port
        self._monitor: FritzMonitor | None = None
        self._attributes: dict[str, str | list[str] | bool] = {}

        self._attr_translation_placeholders = {"phonebook_name": phonebook_name}
        self._attr_unique_id = unique_id
        self._attr_native_value = CallState.IDLE
        self._attr_device_info = DeviceInfo(
            configuration_url=self._fritzbox_phonebook.fph.fc.address,
            identifiers={(DOMAIN, unique_id)},
            manufacturer=MANUFACTURER,
            model=self._fritzbox_phonebook.fph.modelname,
            name=self._fritzbox_phonebook.fph.modelname,
            sw_version=self._fritzbox_phonebook.fph.fc.system_version,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self.hass.async_add_executor_job(self._start_call_monitor)
        self.async_on_remove(
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._stop_call_monitor)
        )

    def _start_call_monitor(self) -> None:
        self._monitor = FritzMonitor(address=self._host, port=self._port)
        q = self._monitor.start(reconnect_tries=50, reconnect_delay=120)
        Thread(target=self._process_events, args=(q,), daemon=True).start()

    def _stop_call_monitor(self, event: Event | None = None) -> None:
        if self._monitor and self._monitor.is_alive:
            self._monitor.stop()

    def _process_events(self, event_queue: queue.Queue[str]) -> None:
        while True:
            try:
                ev = event_queue.get(timeout=10)
            except queue.Empty:
                continue
            _LOGGER.debug("Event: %s", ev)
            self._parse(ev)
            sleep(1)

    def _parse(self, event: str) -> None:
        line = event.split(";")
        df_in, df_out = "%d.%m.%y %H:%M:%S", "%Y-%m-%dT%H:%M:%S"
        isotime = datetime.strptime(line[0], df_in).strftime(df_out)
        if line[1] == FritzState.RING:
            self._attr_native_value = CallState.RINGING
            contact = self._fritzbox_phonebook.get_contact(line[3])
            self._attributes = {
                "type":"incoming","from":line[3],"to":line[4],
                "device":line[5],"initiated":isotime,
                "from_name":contact.name,"vip":contact.vip
            }
        elif line[1] == FritzState.CALL:
            self._attr_native_value = CallState.DIALING
            contact = self._fritzbox_phonebook.get_contact(line[5])
            self._attributes = {
                "type":"outgoing","from":line[4],"to":line[5],
                "device":line[6],"initiated":isotime,
                "to_name":contact.name,"vip":contact.vip
            }
        elif line[1] == FritzState.CONNECT:
            self._attr_native_value = CallState.TALKING
            contact = self._fritzbox_phonebook.get_contact(line[4])
            self._attributes = {
                "with":line[4],"device":line[3],
                "accepted":isotime,
                "with_name":contact.name,"vip":contact.vip
            }
        elif line[1] == FritzState.DISCONNECT:
            self._attr_native_value = CallState.IDLE
            self._attributes = {"duration":line[3],"closed":isotime}

        self.schedule_update_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, str | bool]:
        return self._attributes
