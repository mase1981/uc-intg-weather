"""Weather media player entity."""

import logging
import os
import base64
from typing import Any, Dict, Optional
import asyncio

from ucapi.media_player import MediaPlayer, Features, States, Attributes, Commands
from ucapi.api_definitions import StatusCodes

_LOG = logging.getLogger(__name__)


async def weather_command_handler(entity, command: str, params: dict[str, Any] | None = None) -> StatusCodes:
    """Handle weather entity commands."""
    _LOG.info(f"Weather command received: {command} with params: {params}")
    
    if command == Commands.ON:
        # Force update weather data
        if hasattr(entity, 'update_weather'):
            await entity.update_weather()
        entity.attributes[Attributes.STATE] = States.ON
        if hasattr(entity, '_api'):
            entity._api.configured_entities.update_attributes(
                entity.id,
                {Attributes.STATE: States.ON}
            )
        return StatusCodes.OK
    elif command == Commands.OFF:
        # Turn off (just change state, don't stop updates)
        entity.attributes[Attributes.STATE] = States.OFF
        if hasattr(entity, '_api'):
            entity._api.configured_entities.update_attributes(
                entity.id,
                {Attributes.STATE: States.OFF}
            )
        return StatusCodes.OK
    elif command == Commands.PLAY_PAUSE:
        # Toggle state
        current_state = entity.attributes.get(Attributes.STATE, States.OFF)
        new_state = States.OFF if current_state == States.ON else States.ON
        entity.attributes[Attributes.STATE] = new_state
        if hasattr(entity, '_api'):
            entity._api.configured_entities.update_attributes(
                entity.id,
                {Attributes.STATE: new_state}
            )
        if new_state == States.ON and hasattr(entity, 'update_weather'):
            await entity.update_weather()
        return StatusCodes.OK
    else:
        _LOG.warning(f"Received unhandled command: {command}")
        return StatusCodes.NOT_IMPLEMENTED


class WeatherEntity(MediaPlayer):
    """Weather display entity as a media player."""
    
    def __init__(self, entity_id: str, name: str, weather_client, location_name: str, api=None):
        # Initialize with basic media player features
        features = [
            Features.ON_OFF,
            Features.PLAY_PAUSE,
            Features.MEDIA_TITLE,
            Features.MEDIA_ARTIST,
            Features.MEDIA_ALBUM,
            Features.MEDIA_IMAGE_URL,
        ]
        
        # Initialize attributes
        initial_attributes = {
            Attributes.STATE: States.ON,
            Attributes.MEDIA_TITLE: location_name,
            Attributes.MEDIA_ARTIST: "Loading...",
            Attributes.MEDIA_ALBUM: "Fetching weather...",
            Attributes.MEDIA_IMAGE_URL: ""
        }
        
        super().__init__(
            identifier=entity_id,
            name=name,
            features=features,
            attributes=initial_attributes,
            cmd_handler=weather_command_handler
        )
        
        self.weather_client = weather_client
        self.location_name = location_name
        self._weather_data = None
        self._api = api
        self._icon_cache = {}
        
    def _get_icon_base64(self, icon_filename: str) -> str:
        """Get the base64 encoded icon data."""
        # Check cache first
        if icon_filename in self._icon_cache:
            return self._icon_cache[icon_filename]
            
        # Get the directory where this script is located (works in package and dev)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_dir = os.path.join(script_dir, "icons")
        icon_path = os.path.join(icon_dir, icon_filename)
        
        # Fallback icons
        fallback_icons = ["sun.png", "cloud.png"]
        
        # Check if icon exists, otherwise try fallbacks
        if not os.path.exists(icon_path):
            _LOG.warning(f"Icon not found: {icon_filename}")
            for fallback in fallback_icons:
                icon_path = os.path.join(icon_dir, fallback)
                if os.path.exists(icon_path):
                    _LOG.info(f"Using fallback icon: {fallback}")
                    break
            else:
                _LOG.error("No fallback icons found")
                return ""
        
        try:
            with open(icon_path, 'rb') as f:
                icon_data = f.read()
                # Convert to base64 data URL
                base64_data = base64.b64encode(icon_data).decode('utf-8')
                data_url = f"data:image/png;base64,{base64_data}"
                # Cache the result
                self._icon_cache[icon_filename] = data_url
                return data_url
        except Exception as e:
            _LOG.error(f"Failed to read icon {icon_path}: {e}")
            return ""
    
    async def update_weather(self) -> None:
        """Update weather data from API."""
        try:
            _LOG.debug("Updating weather data...")
            weather_data = await self.weather_client.get_current_weather()
            
            if weather_data:
                self._weather_data = weather_data
                
                # Update attributes with weather data
                new_attributes = {
                    Attributes.STATE: States.ON,
                    Attributes.MEDIA_TITLE: self.location_name,
                    Attributes.MEDIA_ARTIST: weather_data["temperature"],
                    Attributes.MEDIA_ALBUM: weather_data["description"],
                    Attributes.MEDIA_IMAGE_URL: self._get_icon_base64(weather_data["icon"])
                }
                
                # Update local attributes
                for key, value in new_attributes.items():
                    self.attributes[key] = value
                
                # Notify the remote of attribute changes if we're configured
                if self._api and self._api.configured_entities.contains(self.id):
                    self._api.configured_entities.update_attributes(self.id, new_attributes)
                
                _LOG.info(f"Weather updated: {weather_data['temperature']} - {weather_data['description']}")
            else:
                # API failure - show error state
                error_attributes = {
                    Attributes.STATE: States.OFF,
                    Attributes.MEDIA_TITLE: self.location_name,
                    Attributes.MEDIA_ARTIST: "N/A",
                    Attributes.MEDIA_ALBUM: "Data unavailable",
                    Attributes.MEDIA_IMAGE_URL: self._get_icon_base64("cloud.png")
                }
                
                # Update local attributes
                for key, value in error_attributes.items():
                    self.attributes[key] = value
                
                # Notify the remote of attribute changes if we're configured
                if self._api and self._api.configured_entities.contains(self.id):
                    self._api.configured_entities.update_attributes(self.id, error_attributes)
                
                _LOG.warning("Failed to fetch weather data")
                
        except Exception as e:
            _LOG.error(f"Error updating weather: {e}")
            error_attributes = {
                Attributes.STATE: States.OFF,
                Attributes.MEDIA_TITLE: self.location_name,
                Attributes.MEDIA_ARTIST: "Error",
                Attributes.MEDIA_ALBUM: "Update failed",
                Attributes.MEDIA_IMAGE_URL: self._get_icon_base64("cloud.png")
            }
            
            # Update local attributes
            for key, value in error_attributes.items():
                self.attributes[key] = value
            
            # Notify the remote of attribute changes if we're configured
            if self._api and self._api.configured_entities.contains(self.id):
                self._api.configured_entities.update_attributes(self.id, error_attributes)