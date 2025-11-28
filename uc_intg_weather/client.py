"""Weather API client using Open-Meteo."""

import logging
import ssl
from typing import Dict, Optional, Tuple
import aiohttp
import asyncio
import re
import certifi
from datetime import datetime

_LOG = logging.getLogger(__name__)

class WeatherClient:
    """Client for fetching weather data from Open-Meteo API."""

    # Enhanced day icons with comprehensive coverage
    WEATHER_ICONS_DAY = {
        0: "sun.png",
        1: "sun.png",
        2: "sun-cloud.png",
        3: "cloud.png",
        45: "fog.png",
        48: "fog.png",
        51: "drizzle.png",
        53: "drizzle.png",
        55: "drizzle.png",
        56: "freezing-rain.png",
        57: "freezing-rain.png",
        61: "rain-light.png",
        63: "rain.png",
        65: "rain-heavy.png",
        66: "freezing-rain.png",
        67: "freezing-rain.png",
        71: "snow-light.png",
        73: "snow.png",
        75: "snow-heavy.png",
        77: "snow-heavy.png",
        80: "rain-light.png",
        81: "rain.png",
        82: "rain-heavy.png",
        85: "snow-light.png",
        86: "snow.png",
        87: "hail.png",
        88: "hail.png",
        95: "thunderstorm.png",
        96: "thunderstorm.png",
        99: "thunderstorm.png"
    }
    
    # Enhanced night icons with comprehensive coverage
    WEATHER_ICONS_NIGHT = {
        0: "moon.png",
        1: "moon.png",
        2: "moon-cloud.png",
        3: "cloud.png",
        45: "fog.png",
        48: "fog.png",
        51: "drizzle.png",
        53: "drizzle.png",
        55: "drizzle.png",
        56: "freezing-rain.png",
        57: "freezing-rain.png",
        61: "rain-light.png",
        63: "rain.png",
        65: "rain-heavy.png",
        66: "freezing-rain.png",
        67: "freezing-rain.png",
        71: "snow-light.png",
        73: "snow.png",
        75: "snow-heavy.png",
        77: "snow-heavy.png",
        80: "rain-light.png",
        81: "rain.png",
        82: "rain-heavy.png",
        85: "snow-light.png",
        86: "snow.png",
        87: "hail.png",
        88: "hail.png",
        95: "thunderstorm.png",
        96: "thunderstorm.png",
        99: "thunderstorm.png"
    }
    
    # Enhanced weather descriptions
    WEATHER_DESCRIPTIONS = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Light rain showers",
        81: "Moderate rain showers",
        82: "Heavy rain showers",
        85: "Light snow showers",
        86: "Heavy snow showers",
        87: "Slight hail",
        88: "Heavy hail",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with heavy hail"
    }

    def __init__(self, latitude: float, longitude: float, temperature_unit: str = "fahrenheit"):
        self.latitude = latitude
        self.longitude = longitude
        self.temperature_unit = temperature_unit
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session, ensuring SSL context is used."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self.session

    async def close(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_current_weather(self) -> Optional[Dict]:
        """Fetch current weather data."""
        try:
            session = await self._get_session()

            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": "temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m,is_day",
                "temperature_unit": self.temperature_unit,
                "wind_speed_unit": "mph",
                "timezone": "auto"
            }

            _LOG.debug(f"Fetching weather from {url} with params: {params}")

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    current = data.get("current", {})
                    weather_code = current.get("weather_code", 0)
                    is_day = current.get("is_day", 1)
                    
                    # Select icon based on day/night with enhanced coverage
                    if is_day == 1:
                        icon = self.WEATHER_ICONS_DAY.get(weather_code, "sun.png")
                    else:
                        icon = self.WEATHER_ICONS_NIGHT.get(weather_code, "moon.png")
                    
                    # Use appropriate unit symbol
                    unit_symbol = "°F" if self.temperature_unit == "fahrenheit" else "°C"
                    
                    result = {
                        "temperature": f"{current.get('temperature_2m', 0):.1f}{unit_symbol}",
                        "description": self.WEATHER_DESCRIPTIONS.get(weather_code, "Unknown"),
                        "icon": icon,
                        "humidity": f"{current.get('relative_humidity_2m', 0)}%",
                        "wind_speed": f"{current.get('wind_speed_10m', 0)} mph",
                        "weather_code": weather_code,
                        "is_day": is_day
                    }
                    _LOG.info(f"Weather data received: {result['temperature']} - {result['description']} ({'Day' if is_day else 'Night'})")
                    return result
                else:
                    _LOG.error(f"Weather API returned status {response.status}")
                    text = await response.text()
                    _LOG.error(f"Response: {text}")
                    return None

        except asyncio.TimeoutError:
            _LOG.error("Weather API request timed out")
            return None
        except Exception as e:
            _LOG.error(f"Failed to fetch weather data: {type(e).__name__}: {e}")
            return None

    @staticmethod
    async def geocode_location(location: str) -> Tuple[float, float, str]:
        """Geocode a location string to coordinates."""
        try:
            location = location.strip()
            _LOG.info(f"Geocoding location: '{location}'")
            
            # Updated pattern to support international postal codes (2-10 alphanumeric chars with spaces/hyphens)
            postal_pattern = re.compile(r'^[A-Z0-9\s-]{2,10}$', re.IGNORECASE)
            search_query = location

            if postal_pattern.match(location):
                _LOG.info(f"Detected postal/ZIP code: {search_query}")

            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {"name": search_query, "count": 5, "language": "en", "format": "json"}
            
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=30)

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                _LOG.debug(f"Geocoding request to {url} with params: {params}")

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])

                        if not results:
                            raise ValueError(f"Location '{location}' not found")

                        # For postal codes, prefer results in the user's likely country
                        # but don't filter out non-US results
                        if postal_pattern.match(location):
                            # Check if it looks like a US ZIP (5 digits)
                            if re.match(r'^\d{5}(-\d{4})?$', location):
                                us_results = [r for r in results if r.get("country") == "United States"]
                                if us_results:
                                    results = us_results
                        
                        result = results[0]
                        latitude = result.get("latitude")
                        longitude = result.get("longitude")
                        name = result.get("name", "")
                        country = result.get("country", "")
                        admin1 = result.get("admin1", "")  # State/Province

                        if country == "United States" and admin1:
                            location_name = f"{name}, {admin1}"
                        elif country:
                            location_name = f"{name}, {country}"
                        else:
                            location_name = name

                        _LOG.info(f"Geocoded to: {location_name} ({latitude}, {longitude})")
                        return latitude, longitude, location_name
                    else:
                        text = await response.text()
                        raise ValueError(f"Geocoding API returned status {response.status}: {text}")

        except aiohttp.ClientError as e:
            _LOG.error(f"Network error during geocoding: {e}")
            raise ValueError(f"Network error: Unable to connect to geocoding service")
        except asyncio.TimeoutError:
            _LOG.error("Geocoding request timed out")
            raise ValueError("Request timed out: Unable to geocode location")
        except Exception as e:
            _LOG.error(f"Failed to geocode location '{location}': {e}")
            raise ValueError(f"Failed to find location: {str(e)}")