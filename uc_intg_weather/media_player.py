"""
Weather media player entity for Unfolded Circle Remote.

Displays the current weather for a configured location as a media player tile:
location as title, "time - condition - temperature" as the artist line, and a
weather icon as the album art.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import base64
import logging
import os
from typing import Any

from ucapi import StatusCodes, media_player
from ucapi_framework import MediaPlayerEntity

from uc_intg_weather.config import WeatherConfig
from uc_intg_weather.device import WeatherDevice

_LOG = logging.getLogger(__name__)

_FEATURES = [media_player.Features.ON_OFF]
_FALLBACK_ICONS = ["sun.png", "cloud.png"]


class WeatherMediaPlayer(MediaPlayerEntity):
    """Weather display entity backed by a WeatherDevice."""

    def __init__(self, device_config: WeatherConfig, device: WeatherDevice) -> None:
        self._device = device
        self._icon_cache: dict[str, str] = {}
        entity_id = f"media_player.{device_config.identifier}"

        super().__init__(
            entity_id,
            device_config.name,
            _FEATURES,
            {
                media_player.Attributes.STATE: media_player.States.UNKNOWN,
                media_player.Attributes.MEDIA_TITLE: "",
                media_player.Attributes.MEDIA_ARTIST: "",
                media_player.Attributes.MEDIA_ALBUM: "",
                media_player.Attributes.MEDIA_IMAGE_URL: "",
            },
            device_class=media_player.DeviceClasses.RECEIVER,
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        """Push the current device state to the Remote (coordinator pattern)."""
        if self._device.state == "UNAVAILABLE":
            self.update({media_player.Attributes.STATE: media_player.States.UNAVAILABLE})
            return

        attributes: dict[str, Any] = {
            media_player.Attributes.STATE: media_player.States.ON,
            media_player.Attributes.MEDIA_TITLE: self._device.location_name,
        }

        if self._device.weather_available:
            attributes[media_player.Attributes.MEDIA_ARTIST] = (
                f"{self._device.time_str} • {self._device.description} "
                f"• {self._device.temperature}"
            )
            attributes[media_player.Attributes.MEDIA_ALBUM] = self._device.description
            attributes[media_player.Attributes.MEDIA_IMAGE_URL] = self._get_icon_base64(
                self._device.icon_filename
            )
        else:
            attributes[media_player.Attributes.MEDIA_ARTIST] = (
                f"{self._device.time_str} • Weather unavailable"
            )
            attributes[media_player.Attributes.MEDIA_ALBUM] = "Data unavailable"

        self.update(attributes)

    async def _handle_command(
        self, entity: Any, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        """Handle commands. ON triggers an immediate weather refresh."""
        if cmd_id == media_player.Commands.ON:
            await self._device.refresh_weather()
            return StatusCodes.OK
        if cmd_id in (media_player.Commands.OFF, media_player.Commands.PLAY_PAUSE):
            return StatusCodes.OK
        return StatusCodes.NOT_IMPLEMENTED

    def _get_icon_base64(self, icon_filename: str) -> str:
        """Return a base64 data URL for the given weather icon (cached)."""
        if not icon_filename:
            return ""
        if icon_filename in self._icon_cache:
            return self._icon_cache[icon_filename]

        icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
        icon_path = os.path.join(icon_dir, icon_filename)

        if not os.path.exists(icon_path):
            _LOG.warning("Icon not found: %s", icon_filename)
            for fallback in _FALLBACK_ICONS:
                candidate = os.path.join(icon_dir, fallback)
                if os.path.exists(candidate):
                    icon_path = candidate
                    break
            else:
                return ""

        try:
            with open(icon_path, "rb") as f:
                data_url = "data:image/png;base64," + base64.b64encode(f.read()).decode(
                    "utf-8"
                )
            self._icon_cache[icon_filename] = data_url
            return data_url
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("Failed to read icon %s: %s", icon_path, err)
            return ""
