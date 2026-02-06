"""
Platform for Typhoon Sensor integration.
"""

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import async_timeout
from bs4 import BeautifulSoup
from haversine import haversine
from datetime import timedelta
import logging
import re

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up the Typhoon Sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        TyphoonNameSensor(coordinator, entry),
        TyphoonClassificationSensor(coordinator, entry),
        TyphoonDistanceSensor(coordinator, entry),
        TyphoonDetailsSensor(coordinator, entry),
    ]
    async_add_entities(sensors, True)

class TyphoonDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Typhoon data."""

    def __init__(self, hass, home_lat, home_lon, scan_interval):
        """Initialize."""
        self.home_coords = (home_lat, home_lon)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=scan_interval),
        )

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        _LOGGER.debug("Starting async_update for Typhoon Coordinator")
        url = "https://www.pagasa.dost.gov.ph/tropical-cyclone/severe-weather-bulletin"
        
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                _LOGGER.debug("Requesting URL: %s", url)
                async with session.get(url) as response:
                    _LOGGER.debug("Response status: %s", response.status)
                    if response.status == 200:
                        html = await response.text()
                        _LOGGER.debug("Response received, length: %d", len(html))
                        soup = BeautifulSoup(html, 'html.parser')
                        return self._parse_typhoon_data(soup)
                    else:
                        _LOGGER.warning("Failed to fetch data: %s", response.status)
                        return self._get_empty_data()
        except Exception as err:
             _LOGGER.error("Error updating typhoon sensor: %s", err)
             return self._get_empty_data()

    def _get_empty_data(self):
        return {
            "name": "No typhoon detected",
            "classification": "None",
            "distance": None,
            "details": "No active typhoon detected"
        }

    def _parse_typhoon_data(self, soup):
        """Parse the PAGASA HTML to extract typhoon data."""
        _LOGGER.debug("Parsing typhoon data from HTML")
        typhoons = []

        # Find the relevant section containing typhoon information
        typhoon_sections = soup.find_all("div", class_="tropical-cyclone-weather-bulletin-page")
        _LOGGER.debug("Found %d typhoon sections", len(typhoon_sections))

        for section in typhoon_sections:
            # Extract typhoon name and classification
            typhoon_name_tag = section.find("h3")
            _LOGGER.debug("Typhoon name tag: %s", typhoon_name_tag)
            classification = "Unknown"
            typhoon_name = "Unknown"
            
            if typhoon_name_tag:
                full_text = typhoon_name_tag.get_text(strip=True)
                if '"' in full_text:
                    parts = full_text.split('"')
                    if len(parts) >= 2:
                        classification = parts[0].strip()
                        typhoon_name = parts[1].strip()
                    else:
                        typhoon_name = full_text
                else:
                    typhoon_name = full_text
            
            # Extract details
            details_tag = section.find("p")
            _LOGGER.debug("Details tag: %s", details_tag)
            details = details_tag.get_text(strip=True) if details_tag else "No details available"

            # Extract coordinates
            lat, lon = None, None
            
            # Try regex match first for (Lat °N, Lon °E) format
            match = re.search(r'\(\s*(\d+\.\d+)\s*°N,\s*(\d+\.\d+)\s*°E\s*\)', details)
            if match:
                try:
                    lat = float(match.group(1))
                    lon = float(match.group(2))
                    _LOGGER.debug("Coordinates found via regex: Lat=%s, Lon=%s", lat, lon)
                except ValueError:
                     _LOGGER.warning("Regex matched but failed to parse floats")

            if lat is None or lon is None:
                for line in details.split("\n"):
                    _LOGGER.debug("Line: %s", line)
                    if "Lat:" in line and "Lon:" in line:
                        try:
                            lat = float(line.split("Lat:")[1].split(",")[0].strip())
                            lon = float(line.split("Lon:")[1].strip())
                            _LOGGER.debug("Lat: %s, Lon: %s", lat, lon)
                        except (ValueError, IndexError):
                            continue

            if lat is not None and lon is not None:
                _LOGGER.debug("Adding typhoon: %s (%s)", typhoon_name, classification)
                typhoons.append({
                    "name": typhoon_name,
                    "classification": classification,
                    "coordinates": (lat, lon),
                    "details": details
                })
            else:
                 _LOGGER.debug("Skipping %s due to missing coordinates", typhoon_name)

        # Find the nearest typhoon to the home coordinates
        nearest_typhoon = None
        nearest_distance = float("inf")
        _LOGGER.debug("Home coordinates: %s", self.home_coords)
        for typhoon in typhoons:
            distance = haversine(self.home_coords, typhoon["coordinates"])
            _LOGGER.debug("Typhoon: %s, Distance: %s", typhoon["name"], distance)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_typhoon = typhoon
        
        if nearest_typhoon:
            _LOGGER.debug("Nearest typhoon: %s at %s km", nearest_typhoon["name"], nearest_distance)
            return {
                "name": nearest_typhoon["name"],
                "classification": nearest_typhoon["classification"],
                "distance": nearest_distance,
                "details": nearest_typhoon["details"]
            }
        
        _LOGGER.debug("No typhoons detected or parsed")
        return self._get_empty_data()


class TyphoonBaseSensor(CoordinatorEntity, Entity):
    """Base class for Typhoon sensors."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._entry = entry

    @property
    def available(self):
        return self._coordinator.last_update_success

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Typhoon Sensor",
            "manufacturer": "PAGASA",
            "model": "Typhoon Monitor",
            "entry_type": "service",
        }

class TyphoonNameSensor(TyphoonBaseSensor):
    @property
    def name(self):
        return "Typhoon Name"
    
    @property
    def unique_id(self):
        return f"{self._entry.entry_id}_name"
    
    @property
    def state(self):
        return self._coordinator.data.get("name")
    
    @property
    def icon(self):
        return "mdi:weather-hurricane"

class TyphoonClassificationSensor(TyphoonBaseSensor):
    @property
    def name(self):
        return "Typhoon Classification"
    
    @property
    def unique_id(self):
        return f"{self._entry.entry_id}_classification"
    
    @property
    def state(self):
        return self._coordinator.data.get("classification")
    
    @property
    def icon(self):
        return "mdi:alert-circle-outline"

class TyphoonDistanceSensor(TyphoonBaseSensor):
    @property
    def name(self):
        return "Typhoon Distance"
    
    @property
    def unique_id(self):
        return f"{self._entry.entry_id}_distance"
    
    @property
    def state(self):
        dist = self._coordinator.data.get("distance")
        return round(dist, 2) if dist else None
    
    @property
    def unit_of_measurement(self):
        return "km"
        
    @property
    def icon(self):
        return "mdi:map-marker-distance"

class TyphoonDetailsSensor(TyphoonBaseSensor):
    @property
    def name(self):
        return "Typhoon Details"
    
    @property
    def unique_id(self):
        return f"{self._entry.entry_id}_details"
    
    @property
    def state(self):
        # State limited to 255 chars, use attribute for full text if needed or truncate
        details = self._coordinator.data.get("details")
        return details[:255] if details else "No details"
    
    @property
    def extra_state_attributes(self):
        return {"full_details": self._coordinator.data.get("details")}
    
    @property
    def icon(self):
        return "mdi:text-box-outline"
