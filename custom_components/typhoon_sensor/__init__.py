"""The Typhoon Sensor integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .sensor import TyphoonDataCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Typhoon Sensor from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    scan_interval = entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    smart_polling = entry.data.get("smart_polling", False)
    idle_poll_interval = entry.data.get("idle_poll_interval", 480)

    coordinator = TyphoonDataCoordinator(
        hass, 
        entry.data.get("latitude"), 
        entry.data.get("longitude"),
        scan_interval,
        smart_polling,
        idle_poll_interval
    )
    
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok