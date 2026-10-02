"""
Weather driver for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging

from ucapi_framework import BaseIntegrationDriver

from uc_intg_weather.config import WeatherConfig
from uc_intg_weather.device import WeatherDevice
from uc_intg_weather.media_player import (
    WeatherMediaPlayer,
    create_weather_daily_entities,
    create_weather_forecast_cards,
    create_weather_forecast_entities,
)
from uc_intg_weather.select import create_weather_unit_selects
from uc_intg_weather.sensor import create_weather_sensors

_LOG = logging.getLogger(__name__)


class WeatherDriver(BaseIntegrationDriver[WeatherDevice, WeatherConfig]):
    """Weather integration driver."""

    def __init__(self):
        super().__init__(
            device_class=WeatherDevice,
            entity_classes=[
                WeatherMediaPlayer,
                create_weather_forecast_cards,
                create_weather_forecast_entities,
                create_weather_daily_entities,
                create_weather_sensors,
                create_weather_unit_selects,
            ],
            driver_id="weather_display",
        )
