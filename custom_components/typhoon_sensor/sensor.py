"""
Platform for Typhoon Sensor integration.
"""

from homeassistant.helpers.entity import Entity

DOMAIN = "typhoon_sensor"

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Typhoon Sensor platform."""
    sensors = [TyphoonSensor()]
    async_add_entities(sensors, True)

class TyphoonSensor(Entity):
    """Representation of a Typhoon Sensor."""

    def __init__(self):
        """Initialize the sensor."""
        self._state = 24
        self._name = "Typhoon Sensor"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        # The state is fixed to 24, so no update logic is needed.
        pass