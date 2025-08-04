"""Configuration management for weather integration."""

import json
import logging
import os
from datetime import datetime
from typing import Optional

_LOG = logging.getLogger(__name__)

class WeatherConfig:
    """Manages weather integration configuration."""
    
    def __init__(self):
        # Use UC_CONFIG_HOME if set, otherwise use default
        config_base = os.getenv("UC_CONFIG_HOME") or os.path.expanduser("~/.config")
        self.config_dir = os.path.join(config_base, "uc_intg_weather")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self._config = {
            "location": "",
            "latitude": 0.0,
            "longitude": 0.0,
            "location_name": "",
            "last_update": None
        }
        _LOG.info(f"Config directory: {self.config_dir}")
        
    async def load(self) -> None:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    self._config.update(loaded_config)
                _LOG.info(f"Configuration loaded successfully from {self.config_file}")
                _LOG.debug(f"Loaded config: {self._config}")
            else:
                _LOG.info(f"No configuration file found at {self.config_file}, using defaults")
        except Exception as e:
            _LOG.error(f"Failed to load configuration: {e}")
            
    async def save(self) -> None:
        """Save configuration to file."""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            _LOG.info(f"Configuration saved successfully to {self.config_file}")
        except Exception as e:
            _LOG.error(f"Failed to save configuration: {e}")
            
    def is_configured(self) -> bool:
        """Check if the integration is properly configured."""
        result = bool(self._config.get("location") and 
                     self._config.get("latitude") and 
                     self._config.get("longitude"))
        _LOG.debug(f"Configuration check: {result} - Location: {self._config.get('location')}, "
                   f"Lat: {self._config.get('latitude')}, Lon: {self._config.get('longitude')}")
        return result
    
    def set_location(self, location: str, latitude: float, longitude: float, location_name: str) -> None:
        """Set location configuration."""
        self._config["location"] = location
        self._config["latitude"] = latitude
        self._config["longitude"] = longitude
        self._config["location_name"] = location_name
        _LOG.info(f"Location set: {location_name} ({latitude}, {longitude})")
        
    def get_latitude(self) -> float:
        """Get configured latitude."""
        return float(self._config.get("latitude", 0.0))
        
    def get_longitude(self) -> float:
        """Get configured longitude."""
        return float(self._config.get("longitude", 0.0))
        
    def get_location_name(self) -> str:
        """Get configured location name."""
        return self._config.get("location_name", "Unknown Location")
        
    def update_last_update(self) -> None:
        """Update the last update timestamp."""
        self._config["last_update"] = datetime.now().isoformat()