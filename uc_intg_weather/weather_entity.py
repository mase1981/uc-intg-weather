"""Weather media player entity."""

import logging
import os
import base64
from typing import Any, Dict, Optional
import asyncio

from ucapi import media_player
from ucapi.api_definitions import StatusCodes

_LOG = logging.getLogger(__name__)


async def weather_command_handler(entity, command: str, params: dict[str, Any] | None = None) -> StatusCodes:
    """Handle weather entity commands."""
    _LOG.info(f"Weather command received: {command} with params: {params}")

    if command == media_player.Commands.ON:
        _LOG.info("Refreshing weather data on user command.")
        if hasattr(entity, 'update_weather'):
            await entity.update_weather()
        return StatusCodes.OK
    elif command == media_player.Commands.OFF:
        return StatusCodes.OK
    elif command == media_player.Commands.PLAY_PAUSE:
        return StatusCodes.OK
    else:
        _LOG.warning(f"Received unhandled command, returning NOT_IMPLEMENTED: {command}")
        return StatusCodes.NOT_IMPLEMENTED


class WeatherEntity(media_player.MediaPlayer):
    """Weather display entity as a media player."""

    def __init__(self, entity_id: str, name: str, weather_client, location_name: str, api=None):
        features = [
            media_player.Features.ON_OFF,
        ]

        initial_attributes = {
            media_player.Attributes.STATE: media_player.States.ON,
            media_player.Attributes.MEDIA_TITLE: location_name,
            media_player.Attributes.MEDIA_ARTIST: "Loading...",
            media_player.Attributes.MEDIA_ALBUM: "Fetching weather...",
            media_player.Attributes.MEDIA_IMAGE_URL: "",
        }

        super().__init__(
            identifier=entity_id,
            name=name,
            features=features,
            attributes=initial_attributes,
            cmd_handler=weather_command_handler,
            device_class=media_player.DeviceClasses.RECEIVER
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
        new_attributes = self.attributes.copy()
        try:
            _LOG.debug("Updating weather data...")
            weather_data = await self.weather_client.get_current_weather()

            if weather_data:
                new_attributes.update({
                    media_player.Attributes.MEDIA_ARTIST: weather_data["temperature"],
                    media_player.Attributes.MEDIA_ALBUM: weather_data["description"],
                    media_player.Attributes.MEDIA_IMAGE_URL: self._get_icon_base64(weather_data["icon"])
                })
                _LOG.info(f"Weather updated: {weather_data['temperature']} - {weather_data['description']}")
            else:
                _LOG.warning("Failed to fetch weather data")
                new_attributes.update({
                    media_player.Attributes.MEDIA_ARTIST: "N/A",
                    media_player.Attributes.MEDIA_ALBUM: "Data unavailable",
                })

        except Exception as e:
            _LOG.error(f"Error updating weather: {e}")
            new_attributes.update({
                media_player.Attributes.MEDIA_ARTIST: "Error",
                media_player.Attributes.MEDIA_ALBUM: "Update failed",
            })

        self.attributes.update(new_attributes)

        if self._api and self._api.configured_entities.contains(self.id):
            self._api.configured_entities.update_attributes(self.id, self.attributes)