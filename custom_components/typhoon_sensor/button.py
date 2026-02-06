"""Button support for Typhoon Sensor."""
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Typhoon Sensor button."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TyphoonRefreshButton(coordinator, entry)], True)

class TyphoonRefreshButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Typhoon Sensor Manual Refresh button."""

    def __init__(self, coordinator, entry):
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry

    @property
    def unique_id(self) -> str:
        """Return the unique ID."""
        return f"{self._entry.entry_id}_refresh"

    @property
    def name(self) -> str:
        """Return the name of the button."""
        return "Manual Refresh"

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:refresh"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Typhoon Sensor",
            "manufacturer": "PAGASA",
            "model": "Typhoon Monitor",
            "entry_type": "service",
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_request_refresh()
