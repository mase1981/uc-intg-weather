"""
Weather configuration for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from dataclasses import dataclass

from ucapi_framework import BaseConfigManager


def build_identifier(latitude: float, longitude: float) -> str:
    """Build a stable, dot-free device identifier from coordinates."""
    lat = str(latitude).replace("-", "n").replace(".", "_")
    lon = str(longitude).replace("-", "n").replace(".", "_")
    return f"weather_{lat}_{lon}"


@dataclass
class WeatherConfig:
    """Weather location configuration."""

    identifier: str
    name: str
    latitude: float
    longitude: float
    location_name: str
    temperature_unit: str = "fahrenheit"
    # "mph", "kmh", "ms" or "kn". Empty (configs before 3.4.0) keeps the 3.3.0
    # behaviour: mph with Fahrenheit, km/h with Celsius.
    wind_unit: str = ""
    # Artwork text size: "normal", "large" or "xlarge" (see TEXT_SIZES).
    text_size: str = "normal"


WIND_UNITS = {"mph": "mph", "kmh": "km/h", "ms": "m/s", "kn": "kn"}
TEMPERATURE_UNITS = {"celsius": "°C", "fahrenheit": "°F"}
TEXT_SIZES = {"normal": "Normal", "large": "Large", "xlarge": "Extra Large"}


def resolve_wind_unit(temperature_unit: str, wind_unit: str) -> str:
    """Return the Open-Meteo wind unit to use for a configuration."""
    if wind_unit in WIND_UNITS:
        return wind_unit
    return "mph" if temperature_unit == "fahrenheit" else "kmh"


class WeatherConfigManager(BaseConfigManager[WeatherConfig]):
    """Configuration manager with automatic JSON persistence."""

    pass
