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

# Die korrekten Service-Namen MÜSSEN mit Doppelpunkt stehen!
SERVICES = ["X_AVM-DE_OnTel:2", "X_AVM-DE_OnTel:1"]

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

        # CallMonitor starten und Queue holen
        self._monitor = FritzMonitor(address=self.host, port=self.port)
        self._event_queue = self._monitor.start()

        # Thread zum Verarbeiten der Queue
        threading.Thread(target=self._event_loop, daemon=True).start()

    def _event_loop(self) -> None:
        """Live-Events aus der Queue lesen."""
        while True:
            try:
                raw = self._event_queue.get(timeout=10)
            except Empty:
                if not self._monitor.is_alive:
                    _LOGGER.error("FritzMonitor-Verbindung verloren, Thread stoppt")
                    break
                continue
            except Exception as err:
                _LOGGER.exception("Fehler beim Lesen aus Monitor-Queue: %s", err)
                break

            call = _parse_monitor_event(raw)
            if call:
                self._calls.append(call)
                self.async_set_updated_data({
                    "calls": list(self._calls),
                    "voicemails": list(self._voicemails),
                })

    async def _async_update_data(self) -> dict:
        """Wird stündlich ausgeführt, um TR-064-Daten zu laden."""
        try:
            if self.fetch_call_history:
                await self.hass.async_add_executor_job(self._fetch_call_history)
            # bis Voicemail-Probleme geklärt sind, nicht abrufen
            # if self.fetch_voicemails:
            #     await self.hass.async_add_executor_job(self._fetch_voicemails)
        except Exception as err:
            raise UpdateFailed(f"Fehler beim Abrufen via TR-064: {err}") from err

        # nur die letzten 60 Tage behalten
        cutoff = datetime.now() - timedelta(days=60)
        self._calls = [c for c in self._calls if c["datetime"] >= cutoff]

        return {
            "calls": list(self._calls),
            "voicemails": list(self._voicemails),
        }

    def _fetch_call_history(self) -> None:
        """Komplette History via TR-064 abrufen und interne Liste ersetzen."""
        fc = FritzConnection(
            address=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
        )

        for service in SERVICES:
            try:
                result = fc.call_action(service, "GetCallList")
                _LOGGER.debug("GetCallList erfolgreich mit %s", service)
                break
            except Exception as err:
                _LOGGER.warning("GetCallList mit %s fehlgeschlagen: %s", service, err)
        else:
            _LOGGER.error("GetCallList ist mit allen SERVICES fehlgeschlagen")
            return

        calls: list[dict] = []
        for item in result.get("NewCallList", {}).get("Call", []):
            calls.append(_parse_call(item))

        # interne Liste ersetzen
        self._calls = calls

    # Voicemail-Funktion bis auf Weiteres auskommentiert,
    # bis Dein Box-OS & Credentials laufen:
    #
    # def _fetch_voicemails(self) -> None:
    #     """Alle Voicemails via TR-064 abrufen und ersetzen."""
    #     fc = FritzConnection(
    #         address=self.host,
    #         port=self.port,
    #         user=self.username,
    #         password=self.password,
    #     )
    #
    #     for service in SERVICES:
    #         try:
    #             result = fc.call_action(service, "GetMessageList")
    #             _LOGGER.debug("GetMessageList erfolgreich mit %s", service)
    #             break
    #         except Exception as err:
    #             _LOGGER.warning("GetMessageList mit %s fehlgeschlagen: %s", service, err)
    #     else:
    #         _LOGGER.error("GetMessageList ist mit allen SERVICES fehlgeschlagen")
    #         return
    #
    #     vms: list[dict] = []
    #     for item in result.get("NewMessageList", {}).get("Message", []):
    #         vms.append(_parse_voicemail(item))
    #     self._voicemails = vms


def _parse_call(item: dict) -> dict:
    """Einzelnen CallList-Eintrag parsen."""
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


def _parse_monitor_event(raw: str) -> dict | None:
    """Live-Event aus Monitor-Queue parsen."""
    from datetime import datetime
    parts = raw.split(";")
    if len(parts) < 2:
        return None

    try:
        dt = datetime.strptime(parts[0], "%d.%m.%y %H:%M:%S")
    except ValueError:
        _LOGGER.warning("Unparsebarer Zeitstempel: %s", parts[0])
        return None

    verb = parts[1]
    if verb not in ("RING", "CALL", "DISCONNECT"):
        return None

    if verb == "RING":
        number = parts[3] if len(parts) > 3 else ""
        call_type = "incoming"
    elif verb == "CALL":
        number = parts[3] if len(parts) > 3 else ""
        call_type = "outgoing"
    else:
        number = ""
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
