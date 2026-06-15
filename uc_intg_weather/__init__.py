"""
Weather integration for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

# Version: single source of truth in driver.json
try:
    _driver_path = Path(__file__).parent.parent / "driver.json"
    with open(_driver_path, "r", encoding="utf-8") as f:
        __version__ = json.load(f).get("version", "0.0.0")
except (FileNotFoundError, json.JSONDecodeError):
    __version__ = "0.0.0"

__all__ = ["__version__", "main"]

_LOG = logging.getLogger(__name__)


def _migrate_legacy_config(config_path: str) -> None:
    """Convert the pre-3.0 flat-dict config.json to the framework list format.

    The old integration stored a single dict
    (latitude/longitude/location_name/temperature_unit). The framework expects a
    list of device-config dicts. This runs once before the config manager loads.
    """
    from uc_intg_weather.config import build_identifier

    cfg_file = os.path.join(config_path, "config.json")
    if not os.path.exists(cfg_file):
        return

    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as err:
        _LOG.warning("Could not read config for migration: %s", err)
        return

    # Already in the new list format - nothing to do.
    if isinstance(data, list):
        return

    if not isinstance(data, dict):
        return

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    migrated: list = []
    if latitude is not None and longitude is not None:
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            location_name = data.get("location_name") or f"Location ({latitude}, {longitude})"
            unit = data.get("temperature_unit", "fahrenheit")
            migrated = [
                {
                    "identifier": build_identifier(latitude, longitude),
                    "name": f"Weather - {location_name}",
                    "latitude": latitude,
                    "longitude": longitude,
                    "location_name": location_name,
                    "temperature_unit": unit,
                }
            ]
            _LOG.info("Migrated legacy weather configuration for '%s'", location_name)
        except (TypeError, ValueError) as err:
            _LOG.warning("Legacy config migration failed: %s", err)
            migrated = []

    try:
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(migrated, f, ensure_ascii=False)
    except OSError as err:
        _LOG.warning("Could not write migrated config: %s", err)


async def main():
    """Main entry point."""
    from ucapi import DeviceStates
    from ucapi_framework import get_config_path

    from uc_intg_weather.config import WeatherConfig, WeatherConfigManager
    from uc_intg_weather.driver import WeatherDriver
    from uc_intg_weather.setup_flow import WeatherSetupFlow

    level = os.getenv("UC_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s",
    )
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("websockets.server").setLevel(logging.CRITICAL)

    _LOG.info("Starting Weather Integration v%s", __version__)

    driver = WeatherDriver()

    config_path = get_config_path(driver.api.config_dir_path or "")
    _LOG.info("Using configuration path: %s", config_path)

    _migrate_legacy_config(config_path)

    config_manager = WeatherConfigManager(
        config_path,
        add_handler=driver.on_device_added,
        remove_handler=driver.on_device_removed,
        config_class=WeatherConfig,
    )
    driver.config_manager = config_manager

    setup_handler = WeatherSetupFlow.create_handler(driver)

    driver_json = os.path.join(os.path.dirname(__file__), "..", "driver.json")
    await driver.api.init(os.path.abspath(driver_json), setup_handler)

    await driver.register_all_device_instances(connect=False)

    device_count = len(list(config_manager.all()))
    await driver.api.set_device_state(
        DeviceStates.CONNECTED if device_count > 0 else DeviceStates.DISCONNECTED
    )
    _LOG.info("Weather integration started - %d location(s) configured", device_count)

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
