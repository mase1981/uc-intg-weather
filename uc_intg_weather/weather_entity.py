# uc_intg_weather/weather_entity.py

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
        # Treat the ON command as a "Refresh" action
        _LOG.info("Refreshing weather data on user command.")
        if hasattr(entity, 'update_weather'):
            await entity.update_weather()
        return StatusCodes.OK
    else:
        # For any other command, state it's not implemented.
        _LOG.warning(f"Received unhandled command, ignoring: {command}")
        return StatusCodes.NOT_IMPLEMENTED


class WeatherEntity(MediaPlayer):
    """Weather display entity as a media player."""

    def __init__(self, entity_id: str, name: str, weather_client, location_name: str, api=None):
        features = [
            Features.ON_OFF,
            Features.MEDIA_TITLE,
            Features.MEDIA_ARTIST,
            Features.MEDIA_ALBUM,
            Features.MEDIA_IMAGE_URL,
        ]

        # Define the attributes the constructor officially supports
        initial_attributes = {
            Attributes.STATE: States.ON,
            Attributes.MEDIA_TITLE: location_name,
            Attributes.MEDIA_ARTIST: "Loading...",
            Attributes.MEDIA_ALBUM: "Fetching weather...",
            Attributes.MEDIA_IMAGE_URL: "",
        }

        # Call the parent constructor with only the officially recognized attributes
        super().__init__(
            identifier=entity_id,
            name=name,
            features=features,
            attributes=initial_attributes,
            cmd_handler=weather_command_handler
        )
        
        # *** THE FIX: ***
        # Now, add the custom controls attribute directly. We use the raw string 'media_player_controls'
        # because it's not in the official 'Attributes' enum in the ucapi library.
        self.attributes["media_player_controls"] = [
            ["power"]
        ]

        self.weather_client = weather_client
        self.location_name = location_name
        self._weather_data = None
        self._api = api
        self._icon_cache = {}

    def _get_icon_base64(self, icon_filename: str) -> str:
        """Get the base64 encoded icon data."""
        if icon_filename in self._icon_cache:
            return self._icon_cache[icon_filename]

        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_dir = os.path.join(script_dir, "icons")
        icon_path = os.path.join(icon_dir, icon_filename)
        fallback_icons = ["sun.png", "cloud.png"]

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
                base64_data = base64.b64encode(icon_data).decode('utf-8')
                data_url = f"data:image/png;base64,{base64_data}"
                self._icon_cache[icon_filename] = data_url
                return data_url
        except Exception as e:
            _LOG.error(f"Failed to read icon {icon_path}: {e}")
            return ""

    async def update_weather(self) -> None:
        """Update weather data from API."""
        new_attributes = self.attributes.copy()
        try:
            _LOG.debug("Updating weather data...")
            weather_data = await self.weather_client.get_current_weather()

            if weather_data:
                new_attributes.update({
                    Attributes.MEDIA_ARTIST: weather_data["temperature"],
                    Attributes.MEDIA_ALBUM: weather_data["description"],
                    Attributes.MEDIA_IMAGE_URL: self._get_icon_base64(weather_data["icon"])
                })
                _LOG.info(f"Weather updated: {weather_data['temperature']} - {weather_data['description']}")
            else:
                _LOG.warning("Failed to fetch weather data")
                new_attributes.update({
                    Attributes.MEDIA_ARTIST: "N/A",
                    Attributes.MEDIA_ALBUM: "Data unavailable",
                })

        except Exception as e:
            _LOG.error(f"Error updating weather: {e}")
            new_attributes.update({
                Attributes.MEDIA_ARTIST: "Error",
                Attributes.MEDIA_ALBUM: "Update failed",
            })

        # Update local attributes
        self.attributes.update(new_attributes)

        # Notify the remote of attribute changes if we're configured
        if self._api and self._api.configured_entities.contains(self.id):
            self._api.configured_entities.update_attributes(self.id, self.attributes)