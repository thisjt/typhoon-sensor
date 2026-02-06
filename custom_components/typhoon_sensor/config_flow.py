"""Config flow for Typhoon Sensor integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, MIN_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class TyphoonSensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Typhoon Sensor."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="Typhoon Sensor", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LATITUDE, default=self.hass.config.latitude
                    ): cv.latitude,
                    vol.Required(
                        CONF_LONGITUDE, default=self.hass.config.longitude
                    ): cv.longitude,
                    vol.Required(
                        "scan_interval", default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
                }
            ),
        )