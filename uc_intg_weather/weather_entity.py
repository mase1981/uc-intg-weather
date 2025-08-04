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
        # The entity is always considered 'ON', so we just return OK.
        return StatusCodes.OK
    else:
        # For any other command (like OFF, shuffle, etc.), log it and state it's not implemented.
        # This will prevent the UI from erroring out.
        _LOG.warning(f"Received unhandled command, ignoring: {command}")
        return StatusCodes.NOT_IMPLEMENTED


class WeatherEntity(MediaPlayer):
    """Weather display entity as a media player."""

    def __init__(self, entity_id: str, name: str, weather_client, location_name: str, api=None):
        # We still declare the features we support for API correctness.
        features = [
            Features.ON_OFF,          # The 'power' button, used for refresh
            Features.MEDIA_TITLE,
            Features.MEDIA_ARTIST,
            Features.MEDIA_ALBUM,
            Features.MEDIA_IMAGE_URL,
        ]

        # The entity state is always ON.
        initial_attributes = {
            Attributes.STATE: States.ON,
            Attributes.MEDIA_TITLE: location_name,
            Attributes.MEDIA_ARTIST: "Loading...",
            Attributes.MEDIA_ALBUM: "Fetching weather...",
            Attributes.MEDIA_IMAGE_URL: "",

            # This is the key change: Explicitly define the UI controls.
            # We are creating a single row with just one button: 'power'.
            Attributes.MEDIA_PLAYER_CONTROLS: [
                ["power"]
            ]
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
        try:
            _LOG.debug("Updating weather data...")
            weather_data = await self.weather_client.get_current_weather()

            if weather_data:
                self._weather_data = weather_data
                new_attributes = {
                    Attributes.STATE: States.ON,
                    Attributes.MEDIA_TITLE: self.location_name,
                    Attributes.MEDIA_ARTIST: weather_data["temperature"],
                    Attributes.MEDIA_ALBUM: weather_data["description"],
                    Attributes.MEDIA_IMAGE_URL: self._get_icon_base64(weather_data["icon"])
                }
            else:
                # API failure - show error state
                new_attributes = {
                    Attributes.STATE: States.ON,
                    Attributes.MEDIA_TITLE: self.location_name,
                    Attributes.MEDIA_ARTIST: "N/A",
                    Attributes.MEDIA_ALBUM: "Data unavailable",
                    Attributes.MEDIA_IMAGE_URL: self._get_icon_base64("cloud.png")
                }
                _LOG.warning("Failed to fetch weather data")

        except Exception as e:
            _LOG.error(f"Error updating weather: {e}")
            new_attributes = {
                Attributes.STATE: States.ON,
                Attributes.MEDIA_TITLE: self.location_name,
                Attributes.MEDIA_ARTIST: "Error",
                Attributes.MEDIA_ALBUM: "Update failed",
                Attributes.MEDIA_IMAGE_URL: self._get_icon_base64("cloud.png")
            }

        # Update local attributes
        for key, value in new_attributes.items():
            self.attributes[key] = value

        # Notify the remote of attribute changes if we're configured
        if self._api and self._api.configured_entities.contains(self.id):
            self._api.configured_entities.update_attributes(self.id, self.attributes)
            if "temperature" in new_attributes.get(Attributes.MEDIA_ARTIST, ""):
                 _LOG.info(f"Weather updated: {new_attributes[Attributes.MEDIA_ARTIST]} - {new_attributes[Attributes.MEDIA_ALBUM]}")