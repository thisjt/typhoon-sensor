"""
Typhoon Sensor Integration for Home Assistant
"""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN = "typhoon_sensor"

def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Typhoon Sensor integration."""
    return True