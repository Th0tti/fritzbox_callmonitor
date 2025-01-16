import logging
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity

_LOGGER = logging.getLogger(__name__)

class FritzCallSensor(SensorEntity):
    def __init__(self, coordinator, call_type):
        """Initialize the sensor."""
        super().__init__()
        self.coordinator = coordinator
        self.call_type = call_type

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Fritz!Box {self.call_type.replace('_', ' ').capitalize()}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return len(self.coordinator.data.get(self.call_type, []))

    @property
    def extra_state_attributes(self):
        """Return extra attributes of the sensor."""
        return {
            "calls": self.coordinator.data.get(self.call_type, [])
        }

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Fritz!Box call sensors."""
    coordinator = hass.data[config_entry.entry_id]
    call_types = ["all_calls", "voice_messages", "incoming_calls", "missed_calls", "outgoing_calls"]
    sensors = [FritzCallSensor(coordinator, call_type) for call_type in call_types]
    async_add_entities(sensors)
