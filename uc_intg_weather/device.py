"""
Weather device for Unfolded Circle Remote.

Models one configured weather location as a PollingDevice. The framework binds
the poll loop to the entity subscription lifecycle: polling (and the on-screen
clock) start only when the tile is displayed and stop when it is removed from
view or the Remote enters standby.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from ucapi_framework import PollingDevice

from uc_intg_weather.client import WeatherClient
from uc_intg_weather.config import (
    TEMPERATURE_UNITS,
    WIND_UNITS,
    WeatherConfig,
    resolve_wind_unit,
)

_LOG = logging.getLogger(__name__)

# Poll cadence drives the on-screen clock. The weather API itself is only
# queried when the smart interval below has elapsed.
_CLOCK_INTERVAL = 60

# Smart weather-refresh intervals (seconds) by time of day, to limit network use.
_INTERVAL_NIGHT = 14400  # 23:00-06:00 -> every 4 hours
_INTERVAL_PEAK = 1800    # 06:00-09:00 and 17:00-20:00 -> every 30 minutes
_INTERVAL_DAY = 3600     # otherwise -> every hour


class WeatherDevice(PollingDevice):
    """Polling device representing a single weather location."""

    def __init__(self, device_config: WeatherConfig, **kwargs: Any) -> None:
        super().__init__(device_config, poll_interval=_CLOCK_INTERVAL, **kwargs)
        self._device_config = device_config
        self._client: WeatherClient | None = None
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._state: str = "UNAVAILABLE"
        self._weather_data: dict | None = None
        self._time_str: str = ""
        self._last_fetch: float | None = None

    # ------------------------------------------------------------------
    # Required identity properties
    # ------------------------------------------------------------------
    @property
    def identifier(self) -> str:
        return self._device_config.identifier

    @property
    def name(self) -> str:
        return self._device_config.name

    @property
    def address(self) -> str | None:
        return None

    @property
    def log_id(self) -> str:
        return self._device_config.name

    @property
    def state(self) -> str:
        return self._state

    # ------------------------------------------------------------------
    # State accessors for the entity
    # ------------------------------------------------------------------
    @property
    def location_name(self) -> str:
        return self._device_config.location_name

    @property
    def weather_available(self) -> bool:
        return self._weather_data is not None

    @property
    def temperature(self) -> str:
        return self._weather_data.get("temperature", "") if self._weather_data else ""

    @property
    def description(self) -> str:
        return self._weather_data.get("description", "") if self._weather_data else ""

    @property
    def icon_filename(self) -> str:
        return self._weather_data.get("icon", "") if self._weather_data else ""

    @property
    def time_str(self) -> str:
        return self._time_str

    def hourly_forecast(self, hours_ahead: int) -> dict | None:
        """Return an hourly forecast slot relative to the next forecast hour."""
        if not self._weather_data or hours_ahead < 1:
            return None

        hourly = self._weather_data.get("hourly", {})
        times = hourly.get("time", [])

        if not times:
            return None

        utc_offset_seconds = self._weather_data.get(
            "utc_offset_seconds",
            0,
        )

        location_now = (
            datetime.now(timezone.utc)
            + timedelta(seconds=utc_offset_seconds)
        ).replace(tzinfo=None)

        future_indexes = [
            index
            for index, time_value in enumerate(times)
            if datetime.fromisoformat(time_value) > location_now
        ]

        forecast_position = hours_ahead - 1

        if forecast_position >= len(future_indexes):
            return None

        index = future_indexes[forecast_position]
        forecast_time = datetime.fromisoformat(times[index])

        def hourly_value(
            field: str,
            default: Any,
        ) -> Any:
            values = hourly.get(field, [])

            if not isinstance(values, list) or index >= len(values):
                return default

            value = values[index]
            return default if value is None else value

        weather_code = hourly_value("weather_code", 0)
        is_day = hourly_value("is_day", 1)

        icon_map = (
            WeatherClient.WEATHER_ICONS_DAY
            if is_day
            else WeatherClient.WEATHER_ICONS_NIGHT
        )

        return {
            "time": forecast_time,
            "temperature": hourly_value("temperature_2m", 0.0),
            "weather_code": weather_code,
            "description": WeatherClient.WEATHER_DESCRIPTIONS.get(
                weather_code,
                "Unknown",
            ),
            "icon": icon_map.get(weather_code, "cloud.png"),
            "precipitation_probability": hourly_value(
                "precipitation_probability",
                0,
            ),
            "is_day": is_day,
        }

    # ------------------------------------------------------------------
    # Scene helpers (dynamic artwork)
    # ------------------------------------------------------------------
    @property
    def latitude(self) -> float:
        return self._device_config.latitude

    @property
    def temperature_value(self) -> float | None:
        if not self._weather_data:
            return None
        return self._weather_data.get("temperature_value")

    @property
    def is_day(self) -> bool:
        if not self._weather_data:
            return True
        return bool(self._weather_data.get("is_day", 1))

    @property
    def weather_code(self) -> int:
        if not self._weather_data:
            return 0
        return self._weather_data.get("weather_code", 0)

    def location_now(self) -> datetime:
        """Return the current wall-clock time at the weather location (naive)."""
        utc_offset_seconds = (
            self._weather_data.get("utc_offset_seconds", 0) if self._weather_data else 0
        )
        return (
            datetime.now(timezone.utc) + timedelta(seconds=utc_offset_seconds)
        ).replace(tzinfo=None)

    def _daily_value(self, field: str, day: datetime) -> Any:
        daily = self._weather_data.get("daily", {}) if self._weather_data else {}
        days = daily.get("time", [])
        values = daily.get(field, [])
        key = day.date().isoformat()
        if key in days:
            index = days.index(key)
            if index < len(values):
                return values[index]
        return None

    def daily_value(self, field: str, day: datetime) -> Any:
        """Return one Open-Meteo daily value for the given local day."""
        return self._daily_value(field, day)

    def high_low(self) -> tuple[float, float] | None:
        """Return today's (max, min) temperature at the location."""
        now = self.location_now()
        high = self._daily_value("temperature_2m_max", now)
        low = self._daily_value("temperature_2m_min", now)
        if high is None or low is None:
            return None
        return high, low

    def sky_state(self, when: datetime, is_day: bool) -> tuple[float | None, bool]:
        """Return (position along the sun/moon arc 0..1, golden hour) for a local time."""
        try:
            day = timedelta(days=1)
            sunrise = self._parse(self._daily_value("sunrise", when))
            sunset = self._parse(self._daily_value("sunset", when))
            if sunrise is None or sunset is None or sunset <= sunrise:
                return None, False  # polar day/night or no data

            if is_day:
                start, end = sunrise, sunset
            elif when >= sunset:
                start = sunset
                end = self._parse(self._daily_value("sunrise", when + day)) or sunrise + day
            else:
                start = self._parse(self._daily_value("sunset", when - day)) or sunset - day
                end = sunrise

            span = (end - start).total_seconds()
            if span <= 0:
                return None, False
            position = min(1.0, max(0.0, (when - start).total_seconds() / span))

            golden_window = 45 * 60
            golden = is_day and (
                abs((when - sunrise).total_seconds()) <= golden_window
                or abs((sunset - when).total_seconds()) <= golden_window
            )
            return position, golden
        except (TypeError, ValueError):
            return None, False

    def current_value(self, field: str) -> Any:
        """Return a raw value from the Open-Meteo `current` block."""
        if not self._weather_data:
            return None
        return self._weather_data.get("current", {}).get(field)

    @property
    def wind_unit_label(self) -> str:
        return WIND_UNITS[self.wind_unit]

    @property
    def wind_unit(self) -> str:
        """Open-Meteo wind unit in use ("mph", "kmh", "ms" or "kn")."""
        return resolve_wind_unit(
            self._device_config.temperature_unit, self._device_config.wind_unit
        )

    @property
    def temperature_unit(self) -> str:
        return self._device_config.temperature_unit

    @property
    def temperature_symbol(self) -> str:
        return TEMPERATURE_UNITS.get(self._device_config.temperature_unit, "°F")

    async def set_units(
        self, temperature_unit: str | None = None, wind_unit: str | None = None
    ) -> None:
        """Change display units, persist them and refresh the weather immediately."""
        changes: dict[str, str] = {}
        if temperature_unit in TEMPERATURE_UNITS and temperature_unit != self.temperature_unit:
            changes["temperature_unit"] = temperature_unit
        if wind_unit in WIND_UNITS and wind_unit != self._device_config.wind_unit:
            changes["wind_unit"] = wind_unit
        if not changes:
            return

        self.update_config(**changes)
        if self._client is not None:
            self._client.temperature_unit = self._device_config.temperature_unit
            self._client.wind_unit_setting = self._device_config.wind_unit
        _LOG.info("[%s] Units changed: %s", self.log_id, changes)
        await self.refresh_weather()

    def is_twilight(self, when: datetime) -> bool:
        """True within 40 minutes after sunset or before sunrise (blue hour)."""
        window = timedelta(minutes=40)
        try:
            sunrise = self._parse(self._daily_value("sunrise", when))
            sunset = self._parse(self._daily_value("sunset", when))
        except (TypeError, ValueError):
            return False
        if sunrise and timedelta(0) <= sunrise - when <= window:
            return True
        if sunset and timedelta(0) <= when - sunset <= window:
            return True
        return False

    def daily_forecast(self, days_ahead: int) -> dict | None:
        """Return the daily forecast for today + days_ahead at the location."""
        if not self._weather_data or days_ahead < 1:
            return None
        day = self.location_now() + timedelta(days=days_ahead)

        code = self._daily_value("weather_code", day)
        high = self._daily_value("temperature_2m_max", day)
        low = self._daily_value("temperature_2m_min", day)
        if code is None or high is None or low is None:
            return None

        def value(field: str, default: Any) -> Any:
            result = self._daily_value(field, day)
            return default if result is None else result

        try:
            sunrise = self._parse(self._daily_value("sunrise", day))
            sunset = self._parse(self._daily_value("sunset", day))
        except (TypeError, ValueError):
            sunrise = sunset = None

        return {
            "date": day.date(),
            "weather_code": code,
            "description": WeatherClient.WEATHER_DESCRIPTIONS.get(code, "Unknown"),
            "icon": WeatherClient.WEATHER_ICONS_DAY.get(code, "cloud.png"),
            "high": high,
            "low": low,
            "precipitation_probability": value("precipitation_probability_max", 0),
            "uv_index": value("uv_index_max", None),
            "wind_max": value("wind_speed_10m_max", None),
            "sunrise": sunrise,
            "sunset": sunset,
        }

    @staticmethod
    def _parse(value: Any) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    @property
    def current_hour_forecast(self) -> dict | None:
        """Return the hourly forecast slot containing the current time."""
        if not self._weather_data:
            return None

        hourly = self._weather_data.get("hourly", {})
        times = hourly.get("time", [])

        if not times:
            return None

        utc_offset_seconds = self._weather_data.get(
            "utc_offset_seconds",
            0,
        )

        location_now = (
            datetime.now(timezone.utc)
            + timedelta(seconds=utc_offset_seconds)
        ).replace(tzinfo=None)

        current_hour = location_now.replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        try:
            index = next(
                index
                for index, time_value in enumerate(times)
                if datetime.fromisoformat(time_value) == current_hour
            )
        except StopIteration:
            return None

        def hourly_value(
            field: str,
            default: Any,
        ) -> Any:
            values = hourly.get(field, [])

            if not isinstance(values, list) or index >= len(values):
                return default

            value = values[index]
            return default if value is None else value

        return {
            "weather_code": hourly_value("weather_code", 0),
            "precipitation_probability": hourly_value(
                "precipitation_probability",
                0,
            ),
        }

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    async def connect(self) -> bool:
        """Connect idempotently.

        The framework may call connect() twice in quick succession (device-added
        path + subscribe path). Serialize with a lock so the second call sees the
        poll task already running and returns without spawning a duplicate loop.
        """
        async with self._connect_lock:
            return await super().connect()

    async def establish_connection(self) -> None:
        """Prepare the client and perform an initial weather fetch.

        Called from within connect() while the connect lock is held, so it does
        not re-acquire the lock (asyncio locks are not reentrant). Never raises on
        a transient API failure: the tile must stay available and simply show
        "Weather unavailable" until the next poll succeeds.
        """
        if self._client is None:
            self._client = WeatherClient(
                self._device_config.latitude,
                self._device_config.longitude,
                self._device_config.temperature_unit,
                self._device_config.wind_unit,
            )

        self._state = "ON"
        self._time_str = datetime.now().strftime("%I:%M %p")
        await self._fetch_weather()

    async def poll_device(self) -> None:
        """Update the clock every cycle; refresh weather on the smart interval."""
        self._time_str = datetime.now().strftime("%I:%M %p")

        if self._is_weather_due():
            await self._fetch_weather()

        self.push_update()

    async def disconnect(self) -> None:
        """Stop polling and release the HTTP session."""
        async with self._connect_lock:
            if self._client is not None:
                await self._client.close()

        self._state = "UNAVAILABLE"
        await super().disconnect()

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    async def refresh_weather(self) -> None:
        """Force an immediate weather refresh (used by the ON command)."""
        self._time_str = datetime.now().strftime("%I:%M %p")
        await self._fetch_weather()
        self.push_update()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _is_weather_due(self) -> bool:
        if self._weather_data is None or self._last_fetch is None:
            return True

        elapsed = time.monotonic() - self._last_fetch
        return elapsed >= self._smart_interval()

    @staticmethod
    def _smart_interval() -> int:
        hour = datetime.now().hour

        if hour >= 23 or hour < 6:
            return _INTERVAL_NIGHT

        if 6 <= hour < 9 or 17 <= hour < 20:
            return _INTERVAL_PEAK

        return _INTERVAL_DAY

    async def _fetch_weather(self) -> None:
        if self._client is None:
            return

        try:
            data = await self._client.get_current_weather()

            if data:
                self._weather_data = data
                self._last_fetch = time.monotonic()

                _LOG.info(
                    "[%s] Weather updated: %s - %s",
                    self.log_id,
                    data.get("temperature"),
                    data.get("description"),
                )

            else:
                _LOG.warning("[%s] Weather fetch returned no data", self.log_id)
                self._weather_data = None

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.warning("[%s] Weather fetch failed: %s", self.log_id, err)
            self._weather_data = None
