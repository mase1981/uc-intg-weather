"""
Weather unit select entities for Unfolded Circle Remote.

Lets users switch the temperature and wind speed units straight from the
Remote. The choice is saved to the configuration and the weather is refreshed
immediately.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from __future__ import annotations

import logging
from typing import Any

from ucapi import StatusCodes
from ucapi.select import Attributes, Commands, States
from ucapi_framework import SelectEntity

from uc_intg_weather.config import WeatherConfig
from uc_intg_weather.device import WeatherDevice

_LOG = logging.getLogger(__name__)

# Option label -> configuration value
_TEMPERATURE_OPTIONS = {"Celsius (°C)": "celsius", "Fahrenheit (°F)": "fahrenheit"}
_WIND_OPTIONS = {
    "Miles per hour (mph)": "mph",
    "Kilometres per hour (km/h)": "kmh",
    "Metres per second (m/s)": "ms",
    "Knots (kn)": "kn",
}


class WeatherUnitSelect(SelectEntity):
    """Select entity for one display unit (temperature or wind)."""

    def __init__(
        self,
        device_config: WeatherConfig,
        device: WeatherDevice,
        kind: str,
    ) -> None:
        self._device = device
        self._kind = kind
        self._options = _TEMPERATURE_OPTIONS if kind == "temperature" else _WIND_OPTIONS
        label = "Temperature Unit" if kind == "temperature" else "Wind Unit"

        super().__init__(
            f"select.{device_config.identifier}.{kind}_unit",
            f"Weather {label}",
            {
                Attributes.STATE: States.UNKNOWN,
                Attributes.OPTIONS: [],
                Attributes.CURRENT_OPTION: "",
            },
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    def _current_value(self) -> str:
        if self._kind == "temperature":
            return self._device.temperature_unit
        return self._device.wind_unit

    def _current_option(self) -> str:
        current = self._current_value()
        return next((label for label, value in self._options.items() if value == current), "")

    async def sync_state(self) -> None:
        self.update(
            {
                Attributes.STATE: States.ON,
                Attributes.OPTIONS: list(self._options),
                Attributes.CURRENT_OPTION: self._current_option(),
            }
        )

    async def _handle_command(
        self, entity: Any, cmd_id: str, params: dict[str, Any] | None = None
    ) -> StatusCodes:
        labels = list(self._options)
        current = self._current_option()
        index = labels.index(current) if current in labels else 0

        if cmd_id == Commands.SELECT_OPTION:
            option = (params or {}).get("option", "")
            if option not in self._options:
                return StatusCodes.BAD_REQUEST
        elif cmd_id == Commands.SELECT_FIRST:
            option = labels[0]
        elif cmd_id == Commands.SELECT_LAST:
            option = labels[-1]
        elif cmd_id == Commands.SELECT_NEXT:
            option = labels[(index + 1) % len(labels)]
        elif cmd_id == Commands.SELECT_PREVIOUS:
            option = labels[(index - 1) % len(labels)]
        else:
            return StatusCodes.NOT_IMPLEMENTED

        value = self._options[option]
        try:
            if self._kind == "temperature":
                await self._device.set_units(temperature_unit=value)
            else:
                await self._device.set_units(wind_unit=value)
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("Changing %s unit failed: %s", self._kind, err)
            return StatusCodes.SERVER_ERROR

        await self.sync_state()
        return StatusCodes.OK


def create_weather_unit_selects(
    device_config: WeatherConfig, device: WeatherDevice
) -> list[WeatherUnitSelect]:
    """Create the temperature and wind unit selects for one location."""
    return [
        WeatherUnitSelect(device_config, device, "temperature"),
        WeatherUnitSelect(device_config, device, "wind"),
    ]
