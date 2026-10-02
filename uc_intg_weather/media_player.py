"""
Weather media player entities for Unfolded Circle Remote.

Displays the current weather for a configured location as a media player tile
and provides hourly forecast media player entities.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import base64
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from ucapi import StatusCodes, media_player
from ucapi_framework import MediaPlayerEntity

from uc_intg_weather.config import WeatherConfig
from uc_intg_weather.device import WeatherDevice

_LOG = logging.getLogger(__name__)

# Dynamic artwork needs Pillow; without it the static icons are used.
try:
    from uc_intg_weather import scene as _scene
except Exception as _err:  # pylint: disable=broad-exception-caught
    _scene = None
    _LOG.warning("Dynamic weather artwork disabled, using icons: %s", _err)

_FEATURES = [media_player.Features.ON_OFF]
_FALLBACK_ICONS = ["sun.png", "cloud.png"]

_FORECAST_HOURS = range(1, 7)
_FORECAST_DAYS = range(1, 6)
_COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def _quantize(position: float | None) -> float | None:
    """Round the sun/moon position so the card is redrawn about every 2% of the arc."""
    return None if position is None else round(position * 50) / 50


def _compass(degrees: Any) -> str:
    try:
        return _COMPASS[int((float(degrees) % 360) / 45 + 0.5) % 8]
    except (TypeError, ValueError):
        return ""


def _wind_strength(speed: Any, gusts: Any, unit_label: str) -> float:
    """Map wind speed (and gusts) to 0..1 in quarter steps for the scene."""
    try:
        value = max(float(speed or 0), 0.7 * float(gusts or 0))
    except (TypeError, ValueError):
        return 0.0
    mph = value if unit_label == "mph" else value / 1.609
    return round(min(1.0, max(0.0, (mph - 12) / 25)) * 4) / 4


def _clock(value: datetime | None) -> str:
    return value.strftime("%I:%M %p").lstrip("0") if value else ""


def _degrees(value: Any, fallback: str = "") -> str:
    try:
        return f"{round(float(value))}°"
    except (TypeError, ValueError):
        return fallback


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
        self._scene_key: Any = None
        self._scene_url: str = ""
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
                await self._artwork(self._current_scene, self._device.icon_filename)
            )

        else:
            attributes[media_player.Attributes.MEDIA_TITLE] = (
                f"{self._device.time_str} • Weather unavailable"
            )
            attributes[media_player.Attributes.MEDIA_ARTIST] = ""
            attributes[media_player.Attributes.MEDIA_ALBUM] = ""

        self.update(attributes)

    def _current_scene(self) -> Any:
        """Build the scene for the current conditions."""
        dev = self._device
        now = dev.location_now()
        is_day = dev.is_day
        position, golden = dev.sky_state(now, is_day)

        subtitle = dev.location_name
        high_low = dev.high_low()
        if high_low:
            subtitle = f"{subtitle}  •  H {_degrees(high_low[0])}  L {_degrees(high_low[1])}"

        slots = [dev.hourly_forecast(hours) for hours in _FORECAST_HOURS]
        slots = [slot for slot in slots if slot]

        info = []
        feels = _degrees(dev.current_value("apparent_temperature"))
        if feels:
            info.append(f"Feels {feels}")
        wind_speed = dev.current_value("wind_speed_10m")
        if wind_speed is not None:
            direction = _compass(dev.current_value("wind_direction_10m"))
            info.append(f"Wind {round(float(wind_speed))} {dev.wind_unit_label} {direction}".rstrip())
        uv_index = dev.current_value("uv_index")
        if uv_index is not None and is_day:
            info.append(f"UV {round(float(uv_index))}")

        return _scene.SceneSpec(
            weather_code=dev.weather_code,
            is_day=is_day,
            temperature=_degrees(dev.temperature_value, dev.temperature),
            description=dev.description,
            subtitle=subtitle,
            sky_position=_quantize(position),
            golden=golden,
            moon_phase=round(_scene.moon_phase(datetime.now(timezone.utc)), 2),
            southern=dev.latitude < 0,
            strip_temps=tuple(round(float(slot["temperature"])) for slot in slots),
            strip_pops=tuple(int(slot["precipitation_probability"]) for slot in slots),
            strip_label=f"next {len(slots)}h" if slots else "",
            info_line="  •  ".join(info),
            wind=_wind_strength(
                wind_speed, dev.current_value("wind_gusts_10m"), dev.wind_unit_label
            ),
            twilight=not is_day and dev.is_twilight(now),
        )

    async def _artwork(self, build_scene: Callable[[], Any], fallback_icon: str) -> str:
        """Return the dynamic scene as a data URL, or the static icon on any failure.

        The scene is only re-rendered when its inputs change; otherwise the cached
        image is reused, so the per-minute clock tick does not redraw the card.
        """
        if _scene is not None:
            try:
                spec = build_scene()
                if spec == self._scene_key and self._scene_url:
                    return self._scene_url
                data = await asyncio.to_thread(_scene.render, spec)
                self._scene_url = "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
                self._scene_key = spec
                return self._scene_url
            except Exception as err:  # pylint: disable=broad-exception-caught
                _LOG.warning("Weather scene render failed, using icon: %s", err)
        return self._get_icon_base64(fallback_icon)

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
        self._scene_key: Any = None
        self._scene_url: str = ""
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
                await self._artwork(
                    lambda: self._forecast_scene(forecast, forecast_time, precipitation_label),
                    forecast["icon"],
                )
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

    def _forecast_scene(self, forecast: dict, forecast_time: str, precipitation_label: str) -> Any:
        return _forecast_scene_spec(
            self._device, forecast, forecast_time, precipitation_label, self._hours_ahead
        )


def _forecast_scene_spec(
    device: WeatherDevice,
    forecast: dict,
    forecast_time: str,
    precipitation_label: str,
    hours_ahead: int,
) -> Any:
    is_day = bool(forecast["is_day"])
    position, golden = device.sky_state(forecast["time"], is_day)
    return _scene.SceneSpec(
        weather_code=forecast["weather_code"],
        is_day=is_day,
        temperature=_degrees(forecast["temperature"]),
        description=forecast["description"],
        subtitle=(
            f"{forecast_time}  •  {precipitation_label} "
            f"{forecast['precipitation_probability']}%"
        ),
        sky_position=_quantize(position),
        golden=golden,
        moon_phase=round(
            _scene.moon_phase(datetime.now(timezone.utc) + timedelta(hours=hours_ahead)), 2
        ),
        southern=device.latitude < 0,
    )


class WeatherDailyMediaPlayer(WeatherMediaPlayer):
    """Media player displaying the forecast for one upcoming day."""

    def __init__(
        self,
        device_config: WeatherConfig,
        device: WeatherDevice,
        days_ahead: int,
    ) -> None:
        self._device = device
        self._icon_cache: dict[str, str] = {}
        self._scene_key: Any = None
        self._scene_url: str = ""
        self._days_ahead = days_ahead
        self._temperature_unit_symbol = (
            "°F" if device_config.temperature_unit == "fahrenheit" else "°C"
        )

        entity_name = "Weather Tomorrow" if days_ahead == 1 else f"Weather +{days_ahead} days"

        MediaPlayerEntity.__init__(
            self,
            f"media_player.{device_config.identifier}.forecast_{days_ahead}d",
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
        """Push this daily forecast to the Remote."""
        if self._device.state == "UNAVAILABLE":
            self.update(
                {media_player.Attributes.STATE: media_player.States.UNAVAILABLE}
            )
            return

        forecast = self._device.daily_forecast(self._days_ahead)
        attributes: dict[str, Any] = {
            media_player.Attributes.STATE: media_player.States.ON,
        }

        if forecast:
            date = forecast["date"]
            day_label = "Tomorrow" if self._days_ahead == 1 else date.strftime("%A")
            date_label = f"{date.strftime('%a, %b')} {date.day}"
            precipitation_label = _precipitation_label(forecast["weather_code"])
            unit = self._temperature_unit_symbol

            attributes[media_player.Attributes.MEDIA_TITLE] = (
                f"{date_label} • {forecast['description']}"
            )
            attributes[media_player.Attributes.MEDIA_ARTIST] = (
                f"H {round(float(forecast['high']))}{unit} / "
                f"L {round(float(forecast['low']))}{unit} "
                f"• {precipitation_label} {forecast['precipitation_probability']}%"
            )
            attributes[media_player.Attributes.MEDIA_ALBUM] = ""
            attributes[media_player.Attributes.MEDIA_IMAGE_URL] = await self._artwork(
                lambda: self._daily_scene(forecast, day_label, precipitation_label),
                forecast["icon"],
            )
        else:
            attributes[media_player.Attributes.MEDIA_TITLE] = (
                "Tomorrow" if self._days_ahead == 1 else f"+{self._days_ahead} days"
            )
            attributes[media_player.Attributes.MEDIA_ARTIST] = "Forecast unavailable"
            attributes[media_player.Attributes.MEDIA_ALBUM] = ""

        self.update(attributes)

    def _daily_scene(self, forecast: dict, day_label: str, precipitation_label: str) -> Any:
        info = []
        if forecast["sunrise"] and forecast["sunset"]:
            info.append(f"Sunrise {_clock(forecast['sunrise'])}")
            info.append(f"Sunset {_clock(forecast['sunset'])}")
        if forecast["uv_index"] is not None:
            info.append(f"UV {round(float(forecast['uv_index']))}")

        return _scene.SceneSpec(
            weather_code=forecast["weather_code"],
            is_day=True,
            temperature=_degrees(forecast["high"]),
            description=forecast["description"],
            subtitle=(
                f"{day_label}  •  L {_degrees(forecast['low'])}  •  "
                f"{precipitation_label} {forecast['precipitation_probability']}%"
            ),
            sky_position=0.5,
            info_line="  •  ".join(info),
            wind=_wind_strength(forecast["wind_max"], None, self._device.wind_unit_label),
        )


def create_weather_daily_entities(
    device_config: WeatherConfig,
    device: WeatherDevice,
) -> list[WeatherDailyMediaPlayer]:
    """Create the tomorrow through +5 days forecast entities."""
    return [
        WeatherDailyMediaPlayer(device_config, device, days_ahead)
        for days_ahead in _FORECAST_DAYS
    ]


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
