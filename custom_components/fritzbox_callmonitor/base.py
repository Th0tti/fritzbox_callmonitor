"""Coordinator für live-Events und TR-064-Abruf der Anrufliste."""
from __future__ import annotations
import logging
import threading
from datetime import datetime, timedelta
from queue import Empty

from fritzconnection import FritzConnection
from fritzconnection.core.fritzmonitor import FritzMonitor
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class FritzboxCallUpdateCoordinator(DataUpdateCoordinator[dict]):
    def __init__(
        self,
        hass,
        host: str,
        username: str,
        password: str,
        port: int,
        fetch_call_history: bool,
        fetch_voicemails: bool,
        update_interval: timedelta,
    ) -> None:
        """Init: setze Parameter, starte TR-064-Lader und CallMonitor-Thread."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.fetch_call_history = fetch_call_history
        self.fetch_voicemails = fetch_voicemails

        # interner Speicher
        self._calls: list[dict] = []
        self._voicemails: list[dict] = []

        # 1) CallMonitor starten und Queue holen
        self._monitor = FritzMonitor(address=self.host, port=self.port)
        self._event_queue = self._monitor.start()

        # 2) Hintergrund-Thread zum Lesen der Queue
        threading.Thread(target=self._event_loop, daemon=True).start()

    def _event_loop(self) -> None:
        """Endlosschleife im Thread, um CallMonitor-Events zu verarbeiten."""
        while True:
            try:
                raw = self._event_queue.get(timeout=10)
            except Empty:
                # Healthcheck: Verbindung tot?
                if not self._monitor.is_alive:
                    _LOGGER.error("FritzMonitor-Verbindung verloren, beende Thread")
                    break
                continue
            except Exception as err:
                _LOGGER.exception("Fehler beim Lesen aus Monitor-Queue: %s", err)
                break

            call = _parse_monitor_event(raw)
            if call:
                self._calls.append(call)
                # trigger Update für alle Sensoren
                self.async_set_updated_data({
                    "calls": list(self._calls),
                    "voicemails": list(self._voicemails),
                })

    async def _async_update_data(self) -> dict:
        """Wird stündlich ausgeführt, um TR-064-Daten nachzuladen."""
        try:
            if self.fetch_call_history:
                await self.hass.async_add_executor_job(self._fetch_call_history)
            if self.fetch_voicemails:
                await self.hass.async_add_executor_job(self._fetch_voicemails)
        except Exception as err:
            raise UpdateFailed(f"Fehler beim Abrufen via TR-064: {err}") from err

        # nur Einträge der letzten 60 Tage behalten
        cutoff = datetime.now() - timedelta(days=60)
        self._calls = [c for c in self._calls if c["datetime"] >= cutoff]

        return {
            "calls": list(self._calls),
            "voicemails": list(self._voicemails),
        }

    def _fetch_call_history(self) -> None:
        """Erstmaliger und stündlicher Abruf aller Anrufe via TR-064."""
        fc = FritzConnection(
            address=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
        )
        result = fc.call_action("X_AVM-DE_OnTel:1", "GetCallList")
        for item in result.get("NewCallList", {}).get("Call", []):
            call = _parse_call(item)
            if call not in self._calls:
                self._calls.append(call)

    def _fetch_voicemails(self) -> None:
        """Erstmaliger und stündlicher Abruf aller Sprachnachrichten via TR-064."""
        fc = FritzConnection(
            address=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
        )
        result = fc.call_action("X_AVM-DE_OnTel:1", "GetMessageList")
        for item in result.get("NewMessageList", {}).get("Message", []):
            vm = _parse_voicemail(item)
            if vm not in self._voicemails:
                self._voicemails.append(vm)


def _parse_call(item: dict) -> dict:
    """Parse TR-064 CallList-Eintrag."""
    time_str = item.get("Time", "")
    dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
    type_map = {"1": "missed", "2": "incoming", "3": "outgoing"}
    return {
        "type": type_map.get(item.get("Type"), "unknown"),
        "number": item.get("Caller") or item.get("Called", ""),
        "duration": int(item.get("Duration", 0)),
        "datetime": dt,
        "weekday": dt.strftime("%A"),
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M:%S"),
    }

def _parse_voicemail(item: dict) -> dict:
    """Parse TR-064 MessageList-Eintrag."""
    ts = item.get("Timestamp", "")
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
    return {
        "timestamp": dt,
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M:%S"),
        "url": item.get("MessageURL", ""),
    }

def _parse_monitor_event(raw: str) -> dict | None:
    """Parse einen String aus CallMonitor-Queue in unser dict-Format."""
    parts = raw.split(";")
    if len(parts) < 2:
        return None
    # Datum/Zeit im Format 'DD.MM.YY HH:MM:SS'
    try:
        dt = datetime.strptime(parts[0], "%d.%m.%y %H:%M:%S")
    except ValueError:
        _LOGGER.warning("Unparsebares CallMonitor-Timestamp: %s", parts[0])
        return None

    verb = parts[1]
    if verb not in ("RING", "CALL", "DISCONNECT"):
        return None

    # Nummer je nach Eventtyp
    if verb == "RING":
        number = parts[3] if len(parts) > 3 else ""
        call_type = "incoming"
    elif verb == "CALL":
        number = parts[4] if len(parts) > 4 else ""
        call_type = "outgoing"
    else:  # DISCONNECT
        number = ""  # wir kennen die Nummer erst aus TR-064
        call_type = "missed"

    return {
        "type": call_type,
        "number": number,
        "duration": 0,
        "datetime": dt,
        "weekday": dt.strftime("%A"),
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M:%S"),
    }
