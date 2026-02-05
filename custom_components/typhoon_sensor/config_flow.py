"""
Config flow for Typhoon Sensor integration.
"""

from homeassistant import config_entries
from . import DOMAIN

class TyphoonSensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Typhoon Sensor."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="Typhoon Sensor", data={})

        return self.async_show_form(
            step_id="user", data_schema=None
        )