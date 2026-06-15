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
from datetime import datetime
from typing import Any

from ucapi_framework import PollingDevice

from uc_intg_weather.client import WeatherClient
from uc_intg_weather.config import WeatherConfig

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
