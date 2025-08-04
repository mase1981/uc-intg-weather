# uc_intg_weather/config.py
"""Configuration management for the Weather integration."""

import os
import json
import logging
from typing import Optional

import aiofiles

_LOG = logging.getLogger(__name__)
CONFIG_FILE_NAME = "config.json"

class WeatherConfig:
    """Handles loading and saving of integration configuration."""

    def __init__(self):
        self._config_dir = os.getenv("UC_CONFIG_HOME")
        if not self._config_dir:
            self._config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        
        os.makedirs(self._config_dir, exist_ok=True)
        
        self._config_path = os.path.join(self._config_dir, CONFIG_FILE_NAME)
        _LOG.info(f"Config path set to: {self._config_path}")

        self._data = {
            "location_input": None,
            "latitude": None,
            "longitude": None,
            "location_name": None,
            "temperature_unit": "fahrenheit",  # Default to fahrenheit
        }

    async def load(self):
        """Load configuration from the JSON file."""
        if not os.path.exists(self._config_path):
            _LOG.info(f"Configuration file not found at {self._config_path}, using defaults.")
            return

        try:
            async with aiofiles.open(self._config_path, "r") as f:
                content = await f.read()
                self._data = json.loads(content)
                _LOG.info("Successfully loaded configuration.")
        except Exception as e:
            _LOG.error(f"Failed to load configuration from {self._config_path}: {e}")

    async def save(self):
        """Save the current configuration to the JSON file."""
        try:
            async with aiofiles.open(self._config_path, "w") as f:
                await f.write(json.dumps(self._data, indent=4))
                _LOG.info(f"Successfully saved configuration to {self._config_path}")
        except Exception as e:
            _LOG.error(f"Failed to save configuration: {e}")

    def set_location(self, location_input: str, latitude: float, longitude: float, location_name: str, temperature_unit: str = "fahrenheit"):
        """Update location data."""
        self._data["location_input"] = location_input
        self._data["latitude"] = latitude
        self._data["longitude"] = longitude
        self._data["location_name"] = location_name
        self._data["temperature_unit"] = temperature_unit

    def is_configured(self) -> bool:
        """Check if essential configuration (coordinates) is present."""
        return self._data.get("latitude") is not None and self._data.get("longitude") is not None

    def get_latitude(self) -> Optional[float]:
        """Return the configured latitude."""
        return self._data.get("latitude")

    def get_longitude(self) -> Optional[float]:
        """Return the configured longitude."""
        return self._data.get("longitude")

    def get_location_name(self) -> Optional[str]:
        """Return the friendly location name."""
        return self._data.get("location_name")
    
    def get_temperature_unit(self) -> str:
        """Return the configured temperature unit."""
        return self._data.get("temperature_unit", "fahrenheit")