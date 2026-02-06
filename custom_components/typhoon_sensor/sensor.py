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
        TyphoonImageSensor(coordinator, entry),
        TyphoonMovementSensor(coordinator, entry),
        TyphoonSustainedWindsSensor(coordinator, entry),
        TyphoonGustinessSensor(coordinator, entry),
        TyphoonAdvisoryTimeSensor(coordinator, entry),
        TyphoonNextAdvisoryTimeSensor(coordinator, entry),
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
            "details": "No active typhoon detected",
            "image": None,
            "movement": None,
            "sustained_winds": None,
            "gustiness": None,
            "advisory_time": None,
            "next_advisory_time": None,
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
            details = details_tag.get_text(strip=True) if details_tag else "No details available"

            # Helper to find panel text by heading
            def get_panel_text(heading):
                panels = section.find_all("div", class_="panel")
                for panel in panels:
                    head = panel.find("div", class_="panel-heading")
                    if head and heading.lower() in head.get_text(strip=True).lower():
                        body = panel.find("div", class_="panel-body")
                        if body:
                            return body.get_text(strip=True)
                return None

            image_url = None
            img_tag = section.find("img", class_="img-responsive image-preview")
            if img_tag and img_tag.get("src"):
                src = img_tag.get("src")
                if src.startswith("http"):
                    image_url = src
                else:
                    image_url = f"https://pubfiles.pagasa.dost.gov.ph{src}" if src.startswith("/") else f"https://pubfiles.pagasa.dost.gov.ph/{src}"

            movement = get_panel_text("Movement")
            
            strength_text = get_panel_text("Strength")
            sustained_winds = None
            gustiness = None
            if strength_text:
                sust_match = re.search(r"sustained winds of (\d+)", strength_text)
                gust_match = re.search(r"gustiness of up to (\d+)", strength_text)
                if sust_match: sustained_winds = int(sust_match.group(1))
                if gust_match: gustiness = int(gust_match.group(1))

            advisory_time = None
            # Find Issued at ...
            issued_tag = section.find("h5", style=lambda s: s and "margin-bottom" in s) # simple heuristic based on example
            if not issued_tag:
                # Fallback: search all h5
                for h5 in section.find_all("h5"):
                    if "Issued at" in h5.get_text():
                        issued_tag = h5
                        break
            if issued_tag:
                advisory_time = issued_tag.get_text(strip=True).replace("Issued at ", "")

            next_advisory_time = None
            # Find next advisory ...
            next_tag = section.find("h5", style=lambda s: s and "margin-top" in s)
            if not next_tag:
                 for h5 in section.find_all("h5"):
                    if "next advisory" in h5.get_text():
                        next_tag = h5
                        break
            if next_tag:
                 # Extract time from text like "(Valid ... issued at 11:00 PM today)"
                 next_text = next_tag.get_text(strip=True)
                 match = re.search(r"issued at ([\d:]+ [AP]M \w+)", next_text)
                 if match:
                     next_advisory_time = match.group(1)
                 else:
                     next_advisory_time = next_text

            # Extract coordinates
            lat, lon = None, None
            match = re.search(r'\(\s*(\d+\.\d+)\s*°N,\s*(\d+\.\d+)\s*°E\s*\)', details)
            if not match:
                 # Try location panel
                 loc_text = get_panel_text("Location of Eye/center")
                 if loc_text:
                     match = re.search(r'\(\s*(\d+\.\d+)\s*°N,\s*(\d+\.\d+)\s*°E\s*\)', loc_text)
            
            if match:
                try:
                    lat = float(match.group(1))
                    lon = float(match.group(2))
                except ValueError: pass

            if lat is None or lon is None:
                for line in details.split("\n"):
                    if "Lat:" in line and "Lon:" in line:
                        try:
                            lat = float(line.split("Lat:")[1].split(",")[0].strip())
                            lon = float(line.split("Lon:")[1].strip())
                        except (ValueError, IndexError): continue

            if lat is not None and lon is not None:
                _LOGGER.debug("Adding typhoon: %s", typhoon_name)
                typhoons.append({
                    "name": typhoon_name,
                    "classification": classification,
                    "coordinates": (lat, lon),
                    "details": details,
                    "image": image_url,
                    "movement": movement,
                    "sustained_winds": sustained_winds,
                    "gustiness": gustiness,
                    "advisory_time": advisory_time,
                    "next_advisory_time": next_advisory_time,
                })

        nearest_typhoon = None
        nearest_distance = float("inf")
        
        for typhoon in typhoons:
            distance = haversine(self.home_coords, typhoon["coordinates"])
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_typhoon = typhoon
        
        if nearest_typhoon:
            return {
                "name": nearest_typhoon["name"],
                "classification": nearest_typhoon["classification"],
                "distance": nearest_distance,
                "details": nearest_typhoon["details"],
                "image": nearest_typhoon["image"],
                "movement": nearest_typhoon["movement"],
                "sustained_winds": nearest_typhoon["sustained_winds"],
                "gustiness": nearest_typhoon["gustiness"],
                "advisory_time": nearest_typhoon["advisory_time"],
                "next_advisory_time": nearest_typhoon["next_advisory_time"],
            }
        
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
    def name(self): return "Typhoon Name"
    @property
    def unique_id(self): return f"{self._entry.entry_id}_name"
    @property
    def state(self): return self._coordinator.data.get("name")
    @property
    def icon(self): return "mdi:weather-hurricane"

class TyphoonClassificationSensor(TyphoonBaseSensor):
    @property
    def name(self): return "Typhoon Classification"
    @property
    def unique_id(self): return f"{self._entry.entry_id}_classification"
    @property
    def state(self): return self._coordinator.data.get("classification")
    @property
    def icon(self): return "mdi:alert-circle-outline"

class TyphoonDistanceSensor(TyphoonBaseSensor):
    @property
    def name(self): return "Typhoon Distance"
    @property
    def unique_id(self): return f"{self._entry.entry_id}_distance"
    @property
    def state(self):
        dist = self._coordinator.data.get("distance")
        return round(dist, 2) if dist else None
    @property
    def unit_of_measurement(self): return "km"
    @property
    def icon(self): return "mdi:map-marker-distance"

class TyphoonDetailsSensor(TyphoonBaseSensor):
    @property
    def name(self): return "Typhoon Details"
    @property
    def unique_id(self): return f"{self._entry.entry_id}_details"
    @property
    def state(self):
        details = self._coordinator.data.get("details")
        return details[:255] if details else "No details"
    @property
    def extra_state_attributes(self): return {"full_details": self._coordinator.data.get("details")}
    @property
    def icon(self): return "mdi:text-box-outline"

class TyphoonImageSensor(TyphoonBaseSensor):
    @property
    def name(self): return "Typhoon Image"
    @property
    def unique_id(self): return f"{self._entry.entry_id}_image"
    @property
    def state(self): return self._coordinator.data.get("image")
    @property
    def entity_picture(self): return self._coordinator.data.get("image")
    @property
    def icon(self): return "mdi:image"

class TyphoonMovementSensor(TyphoonBaseSensor):
    @property
    def name(self): return "Typhoon Movement"
    @property
    def unique_id(self): return f"{self._entry.entry_id}_movement"
    @property
    def state(self): return self._coordinator.data.get("movement")
    @property
    def icon(self): return "mdi:arrow-expand-all"

class TyphoonSustainedWindsSensor(TyphoonBaseSensor):
    @property
    def name(self): return "Typhoon Maximum Sustained Winds"
    @property
    def unique_id(self): return f"{self._entry.entry_id}_sustained_winds"
    @property
    def state(self): return self._coordinator.data.get("sustained_winds")
    @property
    def unit_of_measurement(self): return "km/h"
    @property
    def icon(self): return "mdi:weather-windy"

class TyphoonGustinessSensor(TyphoonBaseSensor):
    @property
    def name(self): return "Typhoon Gustiness"
    @property
    def unique_id(self): return f"{self._entry.entry_id}_gustiness"
    @property
    def state(self): return self._coordinator.data.get("gustiness")
    @property
    def unit_of_measurement(self): return "km/h"
    @property
    def icon(self): return "mdi:weather-windy-variant"

class TyphoonAdvisoryTimeSensor(TyphoonBaseSensor):
    @property
    def name(self): return "Typhoon Advisory Time"
    @property
    def unique_id(self): return f"{self._entry.entry_id}_advisory_time"
    @property
    def state(self): return self._coordinator.data.get("advisory_time")
    @property
    def icon(self): return "mdi:clock-outline"

class TyphoonNextAdvisoryTimeSensor(TyphoonBaseSensor):
    @property
    def name(self): return "Typhoon Next Advisory Time"
    @property
    def unique_id(self): return f"{self._entry.entry_id}_next_advisory_time"
    @property
    def state(self): return self._coordinator.data.get("next_advisory_time")
    @property
    def icon(self): return "mdi:clock-time-four-outline"
