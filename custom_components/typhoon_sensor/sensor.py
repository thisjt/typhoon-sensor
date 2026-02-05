"""
Platform for Typhoon Sensor integration.
"""

from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE

from homeassistant.helpers.aiohttp_client import async_get_clientsession
import async_timeout
from bs4 import BeautifulSoup
from haversine import haversine
from datetime import timedelta
import logging
import re

DOMAIN = "typhoon_sensor"
SCAN_INTERVAL = timedelta(minutes=30)
_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Typhoon Sensor platform."""
    home_lat = config.get(CONF_LATITUDE, hass.config.latitude)
    home_lon = config.get(CONF_LONGITUDE, hass.config.longitude)

    sensors = [TyphoonSensor(hass, home_lat, home_lon)]
    async_add_entities(sensors, True)

class TyphoonSensor(Entity):
    """Representation of a Typhoon Sensor."""

    def __init__(self, hass, home_lat, home_lon):
        """Initialize the sensor."""
        self.hass = hass
        self._state = None
        self._home_coords = (home_lat, home_lon)
        self._name = "Typhoon Sensor"
        self._attributes = {}

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
        return self._attributes

    async def async_update(self):
        """Fetch new state data for the sensor."""
        _LOGGER.debug("Starting async_update for Typhoon Sensor")
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
                        # TODO: Parse the HTML to extract typhoon data
                        typhoon_data = self._parse_typhoon_data(soup)

                        # Example: Update state and attributes
                        self._state = typhoon_data.get("nearest_typhoon_name", "Unknown")
                        self._attributes = {
                            "last_eye_distance": typhoon_data.get("last_eye_distance"),
                            "next_eye_distance": typhoon_data.get("next_eye_distance"),
                            "classification": typhoon_data.get("classification"),
                            "typhoon_details": typhoon_data.get("details")
                        }
                        _LOGGER.debug("Update finished. State: %s, Attributes: %s", self._state, self._attributes)
                    else:
                        _LOGGER.warning("Failed to fetch data: %s", response.status)
        except Exception as err:
             # Handle timeouts or other errors appropriately for HA (usually just log and keep old state or set to unavailable)
             _LOGGER.error("Error updating typhoon sensor: %s", err)
             self._state = "Unavailable"

    def _parse_typhoon_data(self, soup):
        """Parse the PAGASA HTML to extract typhoon data."""
        typhoons = []

        # Find the relevant section containing typhoon information
        typhoon_sections = soup.find_all("div", class_="tropical-cyclone-weather-bulletin-page")
        for section in typhoon_sections:
            # Extract typhoon name and classification
            typhoon_name_tag = section.find("h3")
            _LOGGER.debug("Typhoon name tag: %s", typhoon_name_tag)
            classification = "Unknown"
            if typhoon_name_tag:
                full_text = typhoon_name_tag.get_text(strip=True)
                _LOGGER.debug("Full text: %s", full_text)
                if '"' in full_text:
                    parts = full_text.split('"')
                    _LOGGER.debug("Parts: %s", parts)
                    if len(parts) >= 2:
                        classification = parts[0].strip()
                        typhoon_name = parts[1].strip()
                    else:
                        typhoon_name = full_text
                else:
                    typhoon_name = full_text
            else:
                typhoon_name = "Unknown"

            # Extract details
            details_tag = section.find("p")
            _LOGGER.debug("Details tag: %s", details_tag)
            details = details_tag.get_text(strip=True) if details_tag else "No details available"

            # Extract coordinates from the details (example: "Lat: 12.3, Lon: 123.4" or "(08.7 °N, 127.2 °E )")
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

        # Find the nearest typhoon to the home coordinates
        nearest_typhoon = None
        nearest_distance = float("inf")
        _LOGGER.debug("Home coordinates: %s", self._home_coords)
        for typhoon in typhoons:
            distance = haversine(self._home_coords, typhoon["coordinates"])
            _LOGGER.debug("Typhoon: %s, Distance: %s", typhoon["name"], distance)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_typhoon = typhoon

        if nearest_typhoon:
            _LOGGER.debug("Nearest typhoon: %s", nearest_typhoon["name"])
            return {
                "nearest_typhoon_name": nearest_typhoon["name"],
                "last_eye_distance": nearest_distance,
                "next_eye_distance": nearest_distance - 10,  # Example calculation
                "details": nearest_typhoon["details"]
            }

        return {
            "nearest_typhoon_name": "No typhoon detected",
            "last_eye_distance": None,
            "next_eye_distance": None,
            "details": None
        }