"""Base für Phonebook, Contact und Coordinator."""
from __future__ import annotations
import logging
import re
import threading
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from queue import Empty

from fritzconnection import FritzConnection
from fritzconnection.lib.fritzphonebook import FritzPhonebook
from fritzconnection.core.fritzmonitor import FritzMonitor

from homeassistant.util import Throttle
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_TR064_PORT,
    DEFAULT_MONITOR_PORT,
    REGEX_NUMBER,
    UNKNOWN_NAME,
)

_LOGGER = logging.getLogger(__name__)

MIN_TIME_PHONEBOOK_UPDATE = timedelta(hours=6)
SERVICES = ["X_AVM-DE_OnTel:2", "X_AVM-DE_OnTel:1"]

@dataclass
class Contact:
    """Ein Kontakt-Eintrag."""
    name: str
    numbers: list[str]
    vip: bool

    def __init__(
        self,
        name: str,
        numbers: list[str] | None = None,
        category: str | None = None,
    ) -> None:
        self.name = name
        self.numbers = [re.sub(REGEX_NUMBER, "", nr) for nr in (numbers or [])]
        self.vip = category == "1"

unknown_contact = Contact(UNKNOWN_NAME)

class FritzBoxPhonebook:
    """Lädt und cached das Telefonbuch."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        phonebook_id: int | None = None,
        prefixes: list[str] | None = None,
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.phonebook_id = phonebook_id
        self.prefixes = prefixes
        self.fph: FritzPhonebook
        self.contacts: list[Contact]
        self.number_dict: dict[str, Contact] = {}

    def init_phonebook(self) -> None:
        self.fph = FritzPhonebook(
            address=self.host, user=self.username, password=self.password
        )
        self.update_phonebook()

    @Throttle(MIN_TIME_PHONEBOOK_UPDATE)
    def update_phonebook(self) -> None:
        if self.phonebook_id is None:
            return
        self.fph.get_all_name_numbers(self.phonebook_id)
        self.contacts = [
            Contact(c.name, c.numbers, getattr(c, "category", None))
            for c in self.fph.phonebook.contacts
        ]
        self.number_dict = {
            nr: c for c in self.contacts for nr in c.numbers
        }

    def get_contact(self, number: str) -> Contact:
        num = re.sub(REGEX_NUMBER, "", str(number))
        with suppress(KeyError):
            return self.number_dict[num]
        if not self.prefixes:
            return unknown_contact
        for prefix in self.prefixes:
            with suppress(KeyError):
                return self.number_dict[prefix + num]
            with suppress(KeyError):
                return self.number_dict[prefix + num.lstrip("0")]
        return unknown_contact

class FritzboxCallUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Coordinator für Live-Events & History."""

    def __init__(
        self,
        hass,
        host: str,
        username: str,
        password: str,
        tr064_port: int = DEFAULT_TR064_PORT,
        monitor_port: int = DEFAULT_MONITOR_PORT,
        fetch_call_history: bool = True,
        fetch_voicemails: bool = False,
        update_interval: timedelta = timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
    ) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.host = host
        self.username = username
        self.password = password
        self.tr064_port = tr064_port
        self.monitor_port = monitor_port
        self.fetch_call_history = fetch_call_history
        self.fetch_voicemails = fetch_voicemails
        self._calls: list[dict] = []
        self._voicemails: list[dict] = []

        # Live-Monitor starten
        self._monitor = FritzMonitor(address=self.host, port=self.monitor_port)
        self._event_queue = self._monitor.start()
        threading.Thread(target=self._event_loop, daemon=True).start()

    def _event_loop(self) -> None:
        while True:
            try:
                raw = self._event_queue.get(timeout=10)
            except Empty:
                if not self._monitor.is_alive:
                    _LOGGER.error("CallMonitor-Verbindung verloren")
                    break
                continue
            call = _parse_monitor_event(raw)
            if call:
                self._calls.append(call)
                self.async_set_updated_data({
                    "calls": list(self._calls),
                    "voicemails": list(self._voicemails),
                })

    async def _async_update_data(self) -> dict:
        try:
            if self.fetch_call_history:
                await self.hass.async_add_executor_job(self._fetch_call_history)
            if self.fetch_voicemails:
                await self.hass.async_add_executor_job(self._fetch_voicemails)
        except Exception as err:
            raise UpdateFailed(f"Fehler beim TR-064-Abruf: {err}") from err

        cutoff = datetime.now() - timedelta(days=60)
        self._calls = [c for c in self._calls if c["datetime"] >= cutoff]
        return {"calls": list(self._calls), "voicemails": list(self._voicemails)}

    def _fetch_call_history(self) -> None:
        fc = FritzConnection(
            address=self.host,
            port=self.tr064_port,
            user=self.username,
            password=self.password,
        )
        for service in SERVICES:
            try:
                result = fc.call_action(service, "GetCallList")
                break
            except Exception as err:
                _LOGGER.warning("GetCallList %s fehlgeschlagen: %s", service, err)
        else:
            _LOGGER.error("GetCallList in allen SERVICES fehlgeschlagen")
            return

        self._calls = [
            _parse_call(item)
            for item in result.get("NewCallList", {}).get("Call", [])
        ]

    def _fetch_voicemails(self) -> None:
        fc = FritzConnection(
            address=self.host,
            port=self.tr064_port,
            user=self.username,
            password=self.password,
        )
        for service in SERVICES:
            try:
                result = fc.call_action(service, "GetMessageList")
                break
            except Exception as err:
                _LOGGER.warning("GetMessageList %s fehlgeschlagen: %s", service, err)
        else:
            return
        self._voicemails = [
            _parse_voicemail(item)
            for item in result.get("NewMessageList", {}).get("Message", [])
        ]

def _parse_call(item: dict) -> dict:
    from datetime import datetime
    dt = datetime.strptime(item.get("Time", ""), "%Y-%m-%dT%H:%M:%S")
    return {
        "type": {"1":"missed","2":"incoming","3":"outgoing"}.get(item.get("Type")),
        "number": item.get("Caller") or item.get("Called"),
        "duration": int(item.get("Duration", 0)),
        "datetime": dt,
        "weekday": dt.strftime("%A"),
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M:%S"),
    }

def _parse_voicemail(item: dict) -> dict:
    from datetime import datetime
    ts = item.get("Timestamp","")
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
    return {"timestamp": dt, "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H:%M:%S"), "url": item.get("MessageURL","")}

def _parse_monitor_event(raw: str) -> dict | None:
    from datetime import datetime
    parts = raw.split(";")
    if len(parts)<2:
        return None
    try:
        dt = datetime.strptime(parts[0], "%d.%m.%y %H:%M:%S")
    except ValueError:
        return None
    verb = parts[1]
    if verb not in ("RING","CALL","DISCONNECT"):
        return None
    num = parts[3] if len(parts)>3 else ""
    tp = {"RING":"incoming","CALL":"outgoing"}.get(verb,"missed")
    return {"type": tp, "number": num, "duration":0,
            "datetime": dt, "weekday": dt.strftime("%A"),
            "date": dt.strftime("%Y-%m-%d"), "time": dt.strftime("%H:%M:%S")}
