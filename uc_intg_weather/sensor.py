"""
Weather sensor entities for Unfolded Circle Remote.

Exposes current conditions as sensors so they can be placed on Remote pages and
used in activities. Units follow the configured temperature and wind units and
are sent with every value (core-api entity_sensor.md: the `unit` attribute takes
precedence and must accompany `value`).

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable

from ucapi.sensor import Attributes, DeviceClasses, States
from ucapi_framework import SensorEntity

from uc_intg_weather.config import WeatherConfig
from uc_intg_weather.device import WeatherDevice

_LOG = logging.getLogger(__name__)

_COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def _number(value: Any, decimals: int = 0) -> float | int | None:
    try:
        number = round(float(value), decimals)
    except (TypeError, ValueError):
        return None
    return int(number) if decimals == 0 else number


def _compass(degrees: Any) -> str | None:
    try:
        return _COMPASS[int((float(degrees) % 360) / 45 + 0.5) % 8]
    except (TypeError, ValueError):
        return None


def _clock(value: datetime | None) -> str | None:
    return value.strftime("%I:%M %p").lstrip("0") if value else None


class WeatherSensor(SensorEntity):
    """One weather value exposed as a sensor."""

    def __init__(
        self,
        device_config: WeatherConfig,
        device: WeatherDevice,
        key: str,
        label: str,
        read: Callable[[WeatherDevice], tuple[Any, str | None]],
        device_class: DeviceClasses = DeviceClasses.CUSTOM,
    ) -> None:
        self._device = device
        self._read = read

        super().__init__(
            f"sensor.{device_config.identifier}.{key}",
            f"Weather {label}",
            [],
            {Attributes.STATE: States.UNKNOWN, Attributes.VALUE: ""},
            device_class=device_class,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({Attributes.STATE: States.UNAVAILABLE})
            return

        value, unit = (None, None)
        if self._device.weather_available:
            try:
                value, unit = self._read(self._device)
            except Exception as err:  # pylint: disable=broad-exception-caught
                _LOG.debug("Sensor %s read failed: %s", self.id, err)

        if value is None:
            self.update({Attributes.STATE: States.UNKNOWN})
            return

        attributes: dict[str, Any] = {Attributes.STATE: States.ON, Attributes.VALUE: value}
        if unit:
            attributes[Attributes.UNIT] = unit
        self.update(attributes)


def _rain_chance(dev: WeatherDevice) -> tuple[Any, str | None]:
    current = dev.current_hour_forecast
    if not current:
        return None, None
    return _number(current["precipitation_probability"]), "%"


def _sun_time(field: str) -> Callable[[WeatherDevice], tuple[Any, str | None]]:
    def read(dev: WeatherDevice) -> tuple[Any, str | None]:
        value = dev.daily_value(field, dev.location_now())
        return _clock(datetime.fromisoformat(value) if value else None), None

    return read


def create_weather_sensors(
    device_config: WeatherConfig, device: WeatherDevice
) -> list[WeatherSensor]:
    """Create the current-conditions sensors for one location."""
    temperature = DeviceClasses.TEMPERATURE
    humidity = DeviceClasses.HUMIDITY
    specs: list[tuple[str, str, Callable[[WeatherDevice], tuple[Any, str | None]], DeviceClasses]] = [
        ("temperature", "Temperature",
         lambda d: (_number(d.temperature_value, 1), d.temperature_symbol), temperature),
        ("feels_like", "Feels Like",
         lambda d: (_number(d.current_value("apparent_temperature"), 1), d.temperature_symbol), temperature),
        ("humidity", "Humidity",
         lambda d: (_number(d.current_value("relative_humidity_2m")), "%"), humidity),
        ("conditions", "Conditions", lambda d: (d.description or None, None), DeviceClasses.CUSTOM),
        ("wind_speed", "Wind Speed",
         lambda d: (_number(d.current_value("wind_speed_10m")), d.wind_unit_label), DeviceClasses.CUSTOM),
        ("wind_gusts", "Wind Gusts",
         lambda d: (_number(d.current_value("wind_gusts_10m")), d.wind_unit_label), DeviceClasses.CUSTOM),
        ("wind_direction", "Wind Direction",
         lambda d: (_compass(d.current_value("wind_direction_10m")), None), DeviceClasses.CUSTOM),
        ("uv_index", "UV Index",
         lambda d: (_number(d.current_value("uv_index")), None), DeviceClasses.CUSTOM),
        ("rain_chance", "Rain Chance", _rain_chance, DeviceClasses.CUSTOM),
        ("sunrise", "Sunrise", _sun_time("sunrise"), DeviceClasses.CUSTOM),
        ("sunset", "Sunset", _sun_time("sunset"), DeviceClasses.CUSTOM),
    ]
    return [
        WeatherSensor(device_config, device, key, label, read, device_class)
        for key, label, read, device_class in specs
    ]
