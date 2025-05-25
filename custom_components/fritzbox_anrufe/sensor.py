"""Sensor platform for fritzbox_anrufe integration."""
import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_IDLE
from homeassistant.helpers.icon import icon_for_staten

from .const import (
    DOMAIN,
    SENSOR_TYPE_CALL_MONITOR,
    SENSOR_DEVICE_CLASS,
    SENSOR_NAME_FORMAT,
    STATE_RINGING,
    STATE_DIALING,
    STATE_TALKING,
    STATE_IDLE,
    ATTR_TYPE,
    ATTR_FROM,
    ATTR_TO,
    ATTR_WITH,
    ATTR_DEVICE,
    ATTR_INITIATED,
    ATTR_ACCEPTED,
    ATTR_CLOSED,
    ATTR_DURATION,
    ATTR_FROM_NAME,
    ATTR_TO_NAME,
    ATTR_WITH_NAME,
    ATTR_VIP,
    ATTR_PREFIXES,
)

_LOGGER = logging.getLogger(__name__)

ICON_MAP = {
    STATE_RINGING: "mdi:phone-ring",
    STATE_DIALING: "mdi:phone-outgoing",
    STATE_TALKING: "mdi:phone",
    STATE_IDLE: "mdi:phone-hangup",
}

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensor for each configured phonebook."""
    base = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FritzCallSensor(base, entry.data)], True)

class FritzCallSensor(SensorEntity):
    """Representation of a Fritz!Box call monitor sensor."""

    def __init__(self, base, config):
        self._base = base
        self._config = config
        self._attr_name = SENSOR_NAME_FORMAT.format(phonebook_id=config[CONF_PHONEBOOK])
        self._attr_unique_id = f"{self._base.fc.system_call_action.sns.serial_number}-{config[CONF_PHONEBOOK]}"
        self._attr_device_class = SENSOR_DEVICE_CLASS
        self._state = None
        self._attr_extra_state_attributes = {}
        hass.bus.async_listen(f"{DOMAIN}_{self._attr_unique_id}", self._handle_event)

    def _handle_event(self, event):
        call = event.data["call"]
        state = call.get("NewState", STATE_IDLE).lower()
        self._state = state
        attrs = {ATTR_PREFIXES: self._config.get(ATTR_PREFIXES, [])}

        if state == STATE_RINGING:
            attrs.update({
                ATTR_TYPE: "incoming",
                ATTR_FROM: call.get("Caller"),
                ATTR_TO: call.get("CalledPartyNumber"),
                ATTR_DEVICE: call.get("Device"),
                ATTR_INITIATED: call.get("Time"),
                ATTR_FROM_NAME: call.get("CallerDisplayName"),
                ATTR_VIP: call.get("VIP"),
            })
        elif state == STATE_DIALING:
            attrs.update({
                ATTR_TYPE: "outgoing",
                ATTR_FROM: call.get("Caller"),
                ATTR_TO: call.get("CalledPartyNumber"),
                ATTR_DEVICE: call.get("Device"),
                ATTR_INITIATED: call.get("Time"),
                ATTR_TO_NAME: call.get("CalledPartyDisplayName"),
                ATTR_VIP: call.get("VIP"),
            })
        elif state == STATE_TALKING:
            attrs.update({
                ATTR_WITH: call.get("Number"),
                ATTR_DEVICE: call.get("Device"),
                ATTR_ACCEPTED: call.get("Time"),
                ATTR_WITH_NAME: call.get("NumberDisplayName"),
                ATTR_VIP: call.get("VIP"),
            })
        else:  # idle
            attrs.update({
                ATTR_DURATION: call.get("Duration"),
                ATTR_CLOSED: call.get("Time"),
            })

        self._attr_extra_state_attributes = attrs
        self.async_write_ha_state()

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return ICON_MAP.get(self._state)
