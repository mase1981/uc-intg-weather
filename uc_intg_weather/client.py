"""Weather API client using Open-Meteo."""

import logging
from typing import Dict, Optional, Tuple
import aiohttp
import asyncio
import re
from datetime import datetime

_LOG = logging.getLogger(__name__)

class WeatherClient:
    """Client for fetching weather data from Open-Meteo API."""
    
    # Weather code to icon mapping (Open-Meteo weather codes)
    # Day icons
    WEATHER_ICONS_DAY = {
        0: "sun.png",           # Clear sky
        1: "sun-cloud.png",     # Mainly clear
        2: "sun-cloud.png",     # Partly cloudy
        3: "cloud.png",         # Overcast
        45: "fog.png",          # Fog
        48: "fog.png",          # Depositing rime fog
        51: "drizzle.png",      # Light drizzle
        53: "drizzle.png",      # Moderate drizzle
        55: "drizzle.png",      # Dense drizzle
        56: "drizzle.png",      # Light freezing drizzle
        57: "drizzle.png",      # Dense freezing drizzle
        61: "rain.png",         # Slight rain
        63: "rain.png",         # Moderate rain
        65: "rain-heavy.png",   # Heavy rain
        66: "rain.png",         # Light freezing rain
        67: "rain-heavy.png",   # Heavy freezing rain
        71: "snow.png",         # Slight snow fall
        73: "snow.png",         # Moderate snow fall
        75: "snow-heavy.png",   # Heavy snow fall
        77: "snow.png",         # Snow grains
        80: "rain.png",         # Slight rain showers
        81: "rain.png",         # Moderate rain showers
        82: "rain-heavy.png",   # Violent rain showers
        85: "snow.png",         # Slight snow showers
        86: "snow-heavy.png",   # Heavy snow showers
        95: "thunderstorm.png", # Thunderstorm
        96: "thunderstorm.png", # Thunderstorm with slight hail
        99: "thunderstorm.png", # Thunderstorm with heavy hail
    }
    
    # Night icons
    WEATHER_ICONS_NIGHT = {
        0: "moon.png",          # Clear sky
        1: "moon-cloud.png",    # Mainly clear
        2: "moon-cloud.png",    # Partly cloudy
        3: "cloud.png",         # Overcast (same day/night)
        45: "fog.png",          # Fog (same day/night)
        48: "fog.png",          # Depositing rime fog
        51: "drizzle.png",      # Light drizzle (same day/night)
        53: "drizzle.png",      # Moderate drizzle
        55: "drizzle.png",      # Dense drizzle
        56: "drizzle.png",      # Light freezing drizzle
        57: "drizzle.png",      # Dense freezing drizzle
        61: "rain.png",         # Slight rain (same day/night)
        63: "rain.png",         # Moderate rain
        65: "rain-heavy.png",   # Heavy rain
        66: "rain.png",         # Light freezing rain
        67: "rain-heavy.png",   # Heavy freezing rain
        71: "snow.png",         # Slight snow fall
        73: "snow.png",         # Moderate snow fall
        75: "snow-heavy.png",   # Heavy snow fall
        77: "snow.png",         # Snow grains
        80: "rain.png",         # Slight rain showers
        81: "rain.png",         # Moderate rain showers
        82: "rain-heavy.png",   # Violent rain showers
        85: "snow.png",         # Slight snow showers
        86: "snow-heavy.png",   # Heavy snow showers
        95: "thunderstorm.png", # Thunderstorm (same day/night)
        96: "thunderstorm.png", # Thunderstorm with slight hail
        99: "thunderstorm.png", # Thunderstorm with heavy hail
    }
    
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
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with heavy hail",
    }
    
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude
        self.session = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
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
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": "auto"
            }
            
            _LOG.debug(f"Fetching weather from {url} with params: {params}")
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    current = data.get("current", {})
                    
                    weather_code = current.get("weather_code", 0)
                    temperature = current.get("temperature_2m", 0)
                    humidity = current.get("relative_humidity_2m", 0)
                    wind_speed = current.get("wind_speed_10m", 0)
                    is_day = current.get("is_day", 1)  # 1 = day, 0 = night
                    
                    # Select appropriate icon based on day/night
                    if is_day == 1:
                        icon = self.WEATHER_ICONS_DAY.get(weather_code, "sun.png")
                    else:
                        icon = self.WEATHER_ICONS_NIGHT.get(weather_code, "moon.png")
                    
                    result = {
                        "temperature": f"{temperature:.1f}°F",
                        "description": self.WEATHER_DESCRIPTIONS.get(weather_code, "Unknown"),
                        "icon": icon,
                        "humidity": f"{humidity}%",
                        "wind_speed": f"{wind_speed} mph",
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
            
            # Check if it's a ZIP code (5 digits, optionally followed by -4 digits)
            zip_pattern = re.compile(r'^\d{5}(-\d{4})?$')
            
            if zip_pattern.match(location):
                # For US ZIP codes, use the ZIP directly - Open-Meteo handles them well
                search_query = location
                _LOG.info(f"Detected ZIP code: {search_query}")
            else:
                # For city/state, keep as is
                search_query = location
            
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {
                "name": search_query,
                "count": 5,  # Get multiple results to find best match
                "language": "en",
                "format": "json"
            }
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                _LOG.debug(f"Geocoding request to {url} with params: {params}")
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        
                        if results:
                            # For ZIP codes, prefer results in the USA
                            if zip_pattern.match(location):
                                us_results = [r for r in results if r.get("country") == "United States"]
                                if us_results:
                                    results = us_results
                            
                            result = results[0]
                            latitude = result.get("latitude")
                            longitude = result.get("longitude")
                            name = result.get("name", "")
                            country = result.get("country", "")
                            admin1 = result.get("admin1", "")  # State/Province
                            
                            # Format location name
                            if country == "United States" and admin1:
                                # For US locations, use "City, State" format
                                location_name = f"{name}, {admin1}"
                            elif country:
                                # For other countries, use "City, Country" format
                                location_name = f"{name}, {country}"
                            else:
                                location_name = name
                            
                            _LOG.info(f"Geocoded to: {location_name} ({latitude}, {longitude})")
                            return latitude, longitude, location_name
                        else:
                            raise ValueError(f"Location '{location}' not found")
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