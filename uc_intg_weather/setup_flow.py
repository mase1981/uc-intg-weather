"""
Weather setup flow for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi import RequestUserInput, SetupError
from ucapi_framework import BaseSetupFlow

from uc_intg_weather.client import WeatherClient
from uc_intg_weather.config import TEXT_SIZES, WIND_UNITS, WeatherConfig, build_identifier

_LOG = logging.getLogger(__name__)


class WeatherSetupFlow(BaseSetupFlow[WeatherConfig]):
    """Setup flow for the Weather integration."""

    def get_manual_entry_form(self) -> RequestUserInput:
        """Collect location (city/ZIP) or coordinates, name, and unit."""
        return self._build_form()

    def _build_form(self, error: str | None = None) -> RequestUserInput:
        settings: list[dict[str, Any]] = []
        if error:
            settings.append(
                {
                    "id": "error",
                    "label": {"en": "Error"},
                    "field": {"label": {"value": {"en": f"⚠️ {error}"}}},
                }
            )
        settings.extend(
            [
                {
                    "id": "location",
                    "label": {"en": "Location (ZIP/Postal code or City, State/Country)"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "latitude",
                    "label": {"en": "Latitude (optional, if not using Location above)"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "longitude",
                    "label": {"en": "Longitude (optional, if not using Location above)"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "location_name",
                    "label": {"en": "Display Name (optional, for lat/lon)"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "use_celsius",
                    "label": {"en": "Use Celsius (°C) instead of Fahrenheit (°F)"},
                    "field": {"checkbox": {"value": False}},
                },
                {
                    "id": "wind_unit",
                    "label": {"en": "Wind speed unit"},
                    "field": {
                        "dropdown": {
                            "value": "auto",
                            "items": [
                                {"id": "auto", "label": {"en": "Automatic (mph with °F, km/h with °C)"}},
                                {"id": "mph", "label": {"en": "Miles per hour (mph)"}},
                                {"id": "kmh", "label": {"en": "Kilometres per hour (km/h)"}},
                                {"id": "ms", "label": {"en": "Metres per second (m/s)"}},
                                {"id": "kn", "label": {"en": "Knots (kn)"}},
                            ],
                        }
                    },
                },
                {
                    "id": "text_size",
                    "label": {"en": "Artwork text size"},
                    "field": {
                        "dropdown": {
                            "value": "normal",
                            "items": [
                                {"id": "normal", "label": {"en": "Normal (most detail)"}},
                                {"id": "large", "label": {"en": "Large (4 hours / 4 days per card)"}},
                                {"id": "xlarge", "label": {"en": "Extra Large (3 hours / 3 days per card)"}},
                            ],
                        }
                    },
                },
            ]
        )
        return RequestUserInput({"en": "Weather Location"}, settings)

    async def query_device(
        self, input_values: dict[str, Any]
    ) -> WeatherConfig | SetupError | RequestUserInput:
        """Validate the location/coordinates against Open-Meteo and build config."""
        location = str(input_values.get("location", "")).strip()
        lat_str = str(input_values.get("latitude", "")).strip()
        lon_str = str(input_values.get("longitude", "")).strip()
        display_name = str(input_values.get("location_name", "")).strip()

        use_celsius = str(input_values.get("use_celsius", False)).strip().lower() == "true"
        temperature_unit = "celsius" if use_celsius else "fahrenheit"
        wind_unit = str(input_values.get("wind_unit", "")).strip()
        if wind_unit not in WIND_UNITS:
            wind_unit = ""
        text_size = str(input_values.get("text_size", "")).strip()
        if text_size not in TEXT_SIZES:
            text_size = "normal"

        # Priority 1: explicit coordinates
        if lat_str and lon_str:
            try:
                latitude = float(lat_str)
                longitude = float(lon_str)
            except ValueError:
                return self._build_form("Latitude and longitude must be numbers.")

            if not -90 <= latitude <= 90:
                return self._build_form("Latitude must be between -90 and 90.")
            if not -180 <= longitude <= 180:
                return self._build_form("Longitude must be between -180 and 180.")

            if not await self._validate(latitude, longitude, temperature_unit):
                return self._build_form(
                    "Unable to fetch weather for those coordinates. Please try again."
                )

            location_name = display_name or f"Location ({latitude}, {longitude})"
            return self._make_config(
                latitude, longitude, location_name, temperature_unit, wind_unit, text_size
            )

        # Priority 2: location string -> geocode
        if location:
            try:
                latitude, longitude, location_name = await WeatherClient.geocode_location(
                    location
                )
            except Exception as err:  # pylint: disable=broad-exception-caught
                _LOG.error("Geocoding failed: %s", err)
                return self._build_form(str(err))

            if not await self._validate(latitude, longitude, temperature_unit):
                return self._build_form(
                    "Found the location but could not fetch weather. Please try again."
                )

            if display_name:
                location_name = display_name
            return self._make_config(
                latitude, longitude, location_name, temperature_unit, wind_unit, text_size
            )

        return self._build_form(
            "Please provide either a location or latitude/longitude coordinates."
        )

    @staticmethod
    async def _validate(latitude: float, longitude: float, unit: str) -> bool:
        client = WeatherClient(latitude, longitude, unit)
        try:
            return bool(await client.get_current_weather())
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("Weather validation failed: %s", err)
            return False
        finally:
            await client.close()

    @staticmethod
    def _make_config(
        latitude: float,
        longitude: float,
        location_name: str,
        unit: str,
        wind_unit: str = "",
        text_size: str = "normal",
    ) -> WeatherConfig:
        identifier = build_identifier(latitude, longitude)
        return WeatherConfig(
            identifier=identifier,
            name=f"Weather - {location_name}",
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            temperature_unit=unit,
            wind_unit=wind_unit,
            text_size=text_size,
        )
