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


class WeatherConfigManager(BaseConfigManager[WeatherConfig]):
    """Configuration manager with automatic JSON persistence."""

    pass
