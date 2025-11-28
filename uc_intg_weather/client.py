"""
Weather API Client for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import os
from typing import Optional, Tuple

import aiohttp
import certifi

_LOG = logging.getLogger(__name__)

ERROR_OS_WAIT = 0.5


class WeatherClient:
    """Client for fetching weather data from Open-Meteo API."""

    def __init__(self, latitude: float, longitude: float, location: str, use_celsius: bool = False):
        self._latitude = latitude
        self._longitude = longitude
        self._location = location
        self._use_celsius = use_celsius
        self._session: Optional[aiohttp.ClientSession] = None
        self._icon_cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
        os.makedirs(self._icon_cache_dir, exist_ok=True)
        _LOG.info(
            f"Weather client initialized for {location} ({latitude}, {longitude}), "
            f"temp unit: {'Celsius' if use_celsius else 'Fahrenheit'}"
        )

    @staticmethod
    async def geocode_location(location: str) -> Tuple[float, float, str]:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json"
        }

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            connector = aiohttp.TCPConnector(ssl=certifi.where())
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url, params=params, ssl=certifi.where()) as response:
                    response.raise_for_status()
                    data = await response.json()

                    if not data.get("results"):
                        _LOG.error(f"Location not found: {location}")
                        raise ValueError(f"Location '{location}' not found. Please verify spelling or try a different format.")

                    result = data["results"][0]
                    latitude = result["latitude"]
                    longitude = result["longitude"]
                    
                    # Build formatted location name
                    name_parts = [result["name"]]
                    if "admin1" in result and result["admin1"]:
                        name_parts.append(result["admin1"])
                    if "country" in result and result["country"]:
                        name_parts.append(result["country"])
                    
                    formatted_name = ", ".join(name_parts)

                    _LOG.info(
                        f"Geocoded '{location}' to: {formatted_name} "
                        f"({latitude}, {longitude})"
                    )

                    return latitude, longitude, formatted_name

        except aiohttp.ClientError as ex:
            _LOG.error(f"Failed to geocode location '{location}': {ex}")
            raise Exception(f"Network error while geocoding location: {ex}")
        except asyncio.TimeoutError:
            _LOG.error(f"Geocoding request timed out for location: {location}")
            raise Exception("Geocoding request timed out. Please try again.")
        except ValueError:
            raise
        except Exception as ex:
            _LOG.error(f"Unexpected error geocoding location '{location}': {ex}")
            raise Exception(f"Failed to geocode location: {ex}")

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            connector = aiohttp.TCPConnector(ssl=certifi.where())
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)

    async def fetch_weather(self) -> dict:
        url = "https://api.open-meteo.com/v1/forecast"

        params = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "current": ["temperature_2m", "weather_code", "is_day"],
            "temperature_unit": "fahrenheit" if not self._use_celsius else "celsius",
            "timezone": "auto"
        }

        try:
            await self._ensure_session()

            async with self._session.get(url, params=params, ssl=certifi.where()) as response:
                response.raise_for_status()
                data = await response.json()

                _LOG.debug(f"Received weather data for {self._location}: {data}")
                return data

        except aiohttp.ClientOSError as ex:
            _LOG.warning(
                f"[{self._location}] OS error detected (WiFi not ready), waiting {ERROR_OS_WAIT}s before retry"
            )

            try:
                await asyncio.sleep(ERROR_OS_WAIT)
                _LOG.info(f"[{self._location}] Retrying weather fetch after WiFi stabilization")

                await self._ensure_session()
                async with self._session.get(url, params=params, ssl=certifi.where()) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data

            except Exception as retry_ex:
                _LOG.error(
                    f"[{self._location}] Weather fetch failed even after WiFi wait period: {retry_ex}"
                )
                raise

        except aiohttp.ClientError as ex:
            _LOG.error(f"Failed to fetch weather data for {self._location}: {ex}")
            raise
        except asyncio.TimeoutError:
            _LOG.error(f"Weather API request timed out for {self._location}")
            raise
        except Exception as ex:
            _LOG.error(f"Unexpected error fetching weather for {self._location}: {ex}")
            raise

    def get_weather_description(self, weather_code: int) -> str:
        descriptions = {
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
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            87: "Slight hail",
            88: "Heavy hail",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }

        return descriptions.get(weather_code, f"Unknown condition (code {weather_code})")

    def _get_weather_icon_url(self, weather_code: int, is_day: int = 1) -> str:
        # Clear sky conditions (0-1) - Day/Night variants
        if weather_code in [0, 1]:
            icon_name = "sun.png" if is_day else "moon.png"

        # Partly cloudy (2) - Day/Night variants
        elif weather_code == 2:
            icon_name = "sun-cloud.png" if is_day else "moon-cloud.png"

        # Overcast (3)
        elif weather_code == 3:
            icon_name = "cloud.png"

        # Fog (45, 48)
        elif weather_code in [45, 48]:
            icon_name = "fog.png"

        # Drizzle (51, 53, 55) - regular drizzle
        elif weather_code in [51, 53, 55]:
            icon_name = "drizzle.png"

        # Freezing drizzle (56, 57)
        elif weather_code in [56, 57]:
            icon_name = "freezing-rain.png"

        # Light rain (61, 80)
        elif weather_code in [61, 80]:
            icon_name = "rain-light.png"

        # Moderate rain (63, 81)
        elif weather_code in [63, 81]:
            icon_name = "rain.png"

        # Heavy rain (65, 82)
        elif weather_code in [65, 82]:
            icon_name = "rain-heavy.png"

        # Freezing rain (66, 67)
        elif weather_code in [66, 67]:
            icon_name = "freezing-rain.png"

        # Light snow (71, 85)
        elif weather_code in [71, 85]:
            icon_name = "snow-light.png"

        # Moderate snow (73, 86)
        elif weather_code in [73, 86]:
            icon_name = "snow.png"

        # Heavy snow (75, 77)
        elif weather_code in [75, 77]:
            icon_name = "snow-heavy.png"

        # Hail (87, 88)
        elif weather_code in [87, 88]:
            icon_name = "hail.png"

        # Thunderstorm (95, 96, 99)
        elif weather_code in [95, 96, 99]:
            icon_name = "thunderstorm.png"

        # Default fallback for any unmapped codes
        else:
            _LOG.warning(f"Unknown weather code {weather_code}, using default cloud icon")
            icon_name = "cloud.png"

        return self._get_icon_path(icon_name)

    def _get_icon_path(self, icon_name: str) -> str:
        icon_path = os.path.join(self._icon_cache_dir, icon_name)

        if not os.path.exists(icon_path):
            _LOG.warning(f"Weather icon not found: {icon_path}, using default")
            icon_path = os.path.join(self._icon_cache_dir, "cloud.png")

        file_url = f"file://{icon_path}"
        _LOG.debug(f"Icon URL for {icon_name}: {file_url}")
        return file_url

    def format_temperature(self, temp: float) -> str:
        unit = "°C" if self._use_celsius else "°F"
        return f"{temp:.1f}{unit}"

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            _LOG.debug("Weather client session closed")