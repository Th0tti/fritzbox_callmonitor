"""Coordinator für live-Events und TR-064-Abruf der Anrufliste."""
from __future__ import annotations
import logging
from datetime import datetime, timedelta

from fritzconnection import FritzConnection
from fritzconnection.core.fritzmonitor import FritzMonitor
from homeassistant.core import callback
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
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.fetch_call_history = fetch_call_history
        self.fetch_voicemails = fetch_voicemails
        self._calls: list[dict] = []
        self._voicemails: list[dict] = []
        self._monitor = FritzMonitor(
            address=self.host,
            port=self.port,
            user=self.username,
            passwd=self.password,
            protocol="http",
            use_tls=False,
        )
        self._monitor.register_callback(self._on_call_event)
        self._monitor.start()

    async def _async_update_data(self) -> dict:
        try:
            if self.fetch_call_history:
                await self.hass.async_add_executor_job(self._fetch_call_history)
            if self.fetch_voicemails:
                await self.hass.async_add_executor_job(self._fetch_voicemails)
        except Exception as err:
            raise UpdateFailed(f"Fehler beim Abrufen: {err}") from err

        cutoff = datetime.now() - timedelta(days=60)
        self._calls = [c for c in self._calls if c["datetime"] >= cutoff]
        return {"calls": list(self._calls), "voicemails": list(self._voicemails)}

    def _fetch_call_history(self) -> None:
        fc = FritzConnection(address=self.host, port=self.port,
                             user=self.username, password=self.password)
        result = fc.call_action("X_AVM-DE_OnTel:1", "GetCallList")
        call_list = result.get("NewCallList", {}).get("Call", [])
        for item in call_list:
            call = _parse_call(item)
            if call not in self._calls:
                self._calls.append(call)

    def _fetch_voicemails(self) -> None:
        fc = FritzConnection(address=self.host, port=self.port,
                             user=self.username, password=self.password)
        result = fc.call_action("X_AVM-DE_OnTel:1", "GetMessageList")
        msgs = result.get("NewMessageList", {}).get("Message", [])
        for item in msgs:
            vm = _parse_voicemail(item)
            if vm not in self._voicemails:
                self._voicemails.append(vm)

    @callback
    def _on_call_event(self, event: dict) -> None:
        call = _parse_monitor_event(event)
        if call:
            self._calls.append(call)
            self.async_set_updated_data(
                {"calls": list(self._calls), "voicemails": list(self._voicemails)}
            )

def _parse_call(item: dict) -> dict:
    from datetime import datetime
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
    from datetime import datetime
    ts = item.get("Timestamp", "")
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
    return {
        "timestamp": dt,
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M:%S"),
        "url": item.get("MessageURL", ""),
    }

def _parse_monitor_event(event: dict) -> dict | None:
    from datetime import datetime
    verb = event.get("Event")
    if verb not in ("RING", "CALL", "DISCONNECT"):
        return None
    call_type = {"RING": "incoming", "CALL": "outgoing", "DISCONNECT": "missed"}[verb]
    ts = event.get("Time", "")
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
    return {
        "type": call_type,
        "number": event.get("Caller") or event.get("Called", ""),
        "duration": 0,
        "datetime": dt,
        "weekday": dt.strftime("%A"),
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M:%S"),
    }

