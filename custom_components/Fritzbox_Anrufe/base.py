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

SERVICES = ["X_AVM-DE_OnTel:2", "X_AVM-DE_OnTel:1"]

class FritzboxCallUpdateCoordinator(DataUpdateCoordinator[dict]):
    def __init__(
        self,
        hass,
        host: str,
        username: str,
        password: str,
        tr064_port: int,
        monitor_port: int,
        fetch_call_history: bool,
        fetch_voicemails: bool,
        update_interval: timedelta,
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

        # CallMonitor starten
        self._monitor = FritzMonitor(address=self.host, port=self.monitor_port)
        self._event_queue = self._monitor.start()
        threading.Thread(target=self._event_loop, daemon=True).start()

    def _event_loop(self) -> None:
        while True:
            try:
                raw = self._event_queue.get(timeout=10)
            except Empty:
                if not self._monitor.is_alive:
                    _LOGGER.error("FritzMonitor-Verbindung verloren")
                    break
                continue
            call = _parse_monitor_event(raw)
            if call:
                self._calls.append(call)
                self.async_set_updated_data({"calls": list(self._calls)})

    async def _async_update_data(self) -> dict:
        try:
            if self.fetch_call_history:
                await self.hass.async_add_executor_job(self._fetch_call_history)
        except Exception as err:
            raise UpdateFailed(f"Fehler beim TR-064-Abruf: {err}") from err

        cutoff = datetime.now() - timedelta(days=60)
        self._calls = [c for c in self._calls if c["datetime"] >= cutoff]
        return {"calls": list(self._calls)}

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
                _LOGGER.warning("GetCallList %s failed: %s", service, err)
        else:
            _LOGGER.error("GetCallList in allen SERVICES fehlgeschlagen")
            return

        self._calls = [
            _parse_call(item)
            for item in result.get("NewCallList", {}).get("Call", [])
        ]

def _parse_call(item: dict) -> dict:
    from datetime import datetime
    dt = datetime.strptime(item.get("Time", ""), "%Y-%m-%dT%H:%M:%S")
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

def _parse_monitor_event(raw: str) -> dict | None:
    from datetime import datetime
    parts = raw.split(";")
    if len(parts) < 2:
        return None
    try:
        dt = datetime.strptime(parts[0], "%d.%m.%y %H:%M:%S")
    except ValueError:
        return None

    verb = parts[1]
    if verb not in ("RING", "CALL", "DISCONNECT"):
        return None
    if verb == "RING":
        number = parts[3] if len(parts) > 3 else ""
        tp = "incoming"
    elif verb == "CALL":
        number = parts[3] if len(parts) > 3 else ""
        tp = "outgoing"
    else:
        number = ""
        tp = "missed"

    return {
        "type": tp,
        "number": number,
        "duration": 0,
        "datetime": dt,
        "weekday": dt.strftime("%A"),
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M:%S"),
    }
