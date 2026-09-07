"""
Weather media player entities for Unfolded Circle Remote.

Displays the current weather for a configured location as a media player tile
and provides hourly forecast media player entities.

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

_FORECAST_HOURS = range(1, 7)


def _precipitation_label(weather_code: int) -> str:
    """Return a short precipitation label for an Open-Meteo weather code."""
    # Drizzle, rain and rain showers
    if weather_code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return "Rain"

    # Freezing drizzle and freezing rain
    if weather_code in (56, 57, 66, 67):
        return "Ice"

    # Snow fall, snow grains and snow showers
    if weather_code in (71, 73, 75, 77, 85, 86):
        return "Snow"

    # Hail and thunderstorms with hail
    if weather_code in (87, 88, 96, 99):
        return "Hail"

    # Thunderstorm without hail
    if weather_code == 95:
        return "Storm"

    # For clear, cloudy and foggy conditions, present the precipitation
    # probability as the chance of rain.
    return "Rain"


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
            self.update(
                {media_player.Attributes.STATE: media_player.States.UNAVAILABLE}
            )
            return

        attributes: dict[str, Any] = {
            media_player.Attributes.STATE: media_player.States.ON,
        }

        if self._device.weather_available:
            current_hour = self._device.current_hour_forecast

            attributes[media_player.Attributes.MEDIA_TITLE] = (
                f"{self._device.time_str} • {self._device.description}"
            )

            if current_hour:
                precipitation_label = _precipitation_label(
                    current_hour["weather_code"]
                )
                precipitation_probability = current_hour[
                    "precipitation_probability"
                ]

                attributes[media_player.Attributes.MEDIA_ARTIST] = (
                    f"{self._device.temperature} "
                    f"• {precipitation_label} "
                    f"{precipitation_probability}%"
                )
            else:
                attributes[media_player.Attributes.MEDIA_ARTIST] = (
                    self._device.temperature
                )

            attributes[media_player.Attributes.MEDIA_ALBUM] = ""

            attributes[media_player.Attributes.MEDIA_IMAGE_URL] = (
                self._get_icon_base64(self._device.icon_filename)
            )

        else:
            attributes[media_player.Attributes.MEDIA_TITLE] = (
                f"{self._device.time_str} • Weather unavailable"
            )
            attributes[media_player.Attributes.MEDIA_ARTIST] = ""
            attributes[media_player.Attributes.MEDIA_ALBUM] = ""

        self.update(attributes)

    async def _handle_command(
        self,
        entity: Any,
        cmd_id: str,
        params: dict[str, Any] | None,
    ) -> StatusCodes:
        """Handle commands. ON triggers an immediate weather refresh."""
        if cmd_id == media_player.Commands.ON:
            await self._device.refresh_weather()
            return StatusCodes.OK

        if cmd_id in (
            media_player.Commands.OFF,
            media_player.Commands.PLAY_PAUSE,
        ):
            return StatusCodes.OK

        return StatusCodes.NOT_IMPLEMENTED

    def _get_icon_base64(self, icon_filename: str) -> str:
        """Return a base64 data URL for the given weather icon (cached)."""
        if not icon_filename:
            return ""

        if icon_filename in self._icon_cache:
            return self._icon_cache[icon_filename]

        icon_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "icons",
        )
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
            with open(icon_path, "rb") as file:
                data_url = (
                    "data:image/png;base64,"
                    + base64.b64encode(file.read()).decode("utf-8")
                )

            self._icon_cache[icon_filename] = data_url
            return data_url

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("Failed to read icon %s: %s", icon_path, err)
            return ""


class WeatherForecastMediaPlayer(WeatherMediaPlayer):
    """Media player displaying one hourly weather forecast slot."""

    def __init__(
        self,
        device_config: WeatherConfig,
        device: WeatherDevice,
        hours_ahead: int,
    ) -> None:
        self._device = device
        self._icon_cache: dict[str, str] = {}
        self._hours_ahead = hours_ahead
        self._temperature_unit_symbol = (
            "°F"
            if device_config.temperature_unit == "fahrenheit"
            else "°C"
        )

        entity_id = (
            f"media_player.{device_config.identifier}."
            f"forecast_{hours_ahead}h"
        )

        if hours_ahead == 1:
            entity_name = "Weather +1 hour"
        else:
            entity_name = f"Weather +{hours_ahead} hours"

        MediaPlayerEntity.__init__(
            self,
            entity_id,
            entity_name,
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
        """Push this hourly forecast slot to the Remote."""
        if self._device.state == "UNAVAILABLE":
            self.update(
                {media_player.Attributes.STATE: media_player.States.UNAVAILABLE}
            )
            return

        forecast = self._device.hourly_forecast(self._hours_ahead)

        attributes: dict[str, Any] = {
            media_player.Attributes.STATE: media_player.States.ON,
        }

        if forecast:
            forecast_time = (
                forecast["time"]
                .strftime("%I:%M %p")
                .lstrip("0")
            )

            temperature = forecast["temperature"]
            description = forecast["description"]
            precipitation_label = _precipitation_label(
                forecast["weather_code"]
            )

            attributes[media_player.Attributes.MEDIA_TITLE] = (
                f"{forecast_time} • {description}"
            )

            attributes[media_player.Attributes.MEDIA_ARTIST] = (
                f"{temperature:.1f}{self._temperature_unit_symbol} "
                f"• {precipitation_label} "
                f"{forecast['precipitation_probability']}%"
            )

            attributes[media_player.Attributes.MEDIA_ALBUM] = ""

            attributes[media_player.Attributes.MEDIA_IMAGE_URL] = (
                self._get_icon_base64(forecast["icon"])
            )

        else:
            hour_text = (
                f"+{self._hours_ahead} hour"
                if self._hours_ahead == 1
                else f"+{self._hours_ahead} hours"
            )

            attributes[media_player.Attributes.MEDIA_TITLE] = hour_text
            attributes[media_player.Attributes.MEDIA_ARTIST] = (
                "Forecast unavailable"
            )
            attributes[media_player.Attributes.MEDIA_ALBUM] = ""

        self.update(attributes)


def create_weather_forecast_entities(
    device_config: WeatherConfig,
    device: WeatherDevice,
) -> list[WeatherForecastMediaPlayer]:
    """Create the +1 through +6 hourly forecast entities."""
    return [
        WeatherForecastMediaPlayer(
            device_config,
            device,
            hours_ahead,
        )
        for hours_ahead in _FORECAST_HOURS
    ]
