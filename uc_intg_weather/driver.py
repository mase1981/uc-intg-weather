"""
Weather integration driver for Unfolded Circle Remote.
Displays current weather conditions using Open-Meteo API.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict
from datetime import datetime

import ucapi
from ucapi import DeviceStates, Events, IntegrationSetupError

from uc_intg_weather.config import WeatherConfig
from uc_intg_weather.client import WeatherClient
from uc_intg_weather.weather_entity import WeatherEntity

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOG = logging.getLogger(__name__)

def get_smart_update_interval():
    """Get update interval based on time of day to save battery."""
    current_hour = datetime.now().hour
    if current_hour >= 23 or current_hour < 6: return 14400
    elif 6 <= current_hour < 9 or 17 <= current_hour < 20: return 1800
    else: return 3600

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

API = ucapi.IntegrationAPI(loop)
CONFIG = WeatherConfig()
WEATHER_ENTITY: WeatherEntity | None = None
UPDATE_TASK: asyncio.Task | None = None
WEATHER_CLIENT: WeatherClient | None = None


async def setup_weather_services():
    """Set up weather client and entity."""
    global WEATHER_CLIENT, WEATHER_ENTITY

    try:
        WEATHER_CLIENT = WeatherClient(
            CONFIG.get_latitude(),
            CONFIG.get_longitude(),
            CONFIG.get_temperature_unit()
        )

        location_name = CONFIG.get_location_name()
        WEATHER_ENTITY = WeatherEntity(
            f"weather-{CONFIG.get_latitude()}-{CONFIG.get_longitude()}".replace(".", "-"),
            f"Weather - {location_name}",
            WEATHER_CLIENT,
            location_name,
            API
        )

        API.available_entities.add(WEATHER_ENTITY)
        await asyncio.sleep(0.5)
        _LOG.info(f"Weather services set up for {location_name}")
        return True

    except Exception as e:
        _LOG.error(f"Failed to setup weather services: {e}")
        return False


def start_weather_updates():
    """Start the periodic weather update task."""
    global UPDATE_TASK
    if UPDATE_TASK and not UPDATE_TASK.done(): return
    _LOG.info("Starting weather update loop...")
    UPDATE_TASK = loop.create_task(weather_update_loop())


async def weather_update_loop():
    """Periodic weather update loop with smart intervals."""
    while True:
        try:
            if WEATHER_ENTITY:
                await WEATHER_ENTITY.update_weather()
            interval = get_smart_update_interval()
            _LOG.info(f"Next weather update in {interval/60} minutes")
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            _LOG.error(f"Error in weather update loop: {e}")
            await asyncio.sleep(300)


async def on_setup_complete():
    """Called when setup is complete."""
    _LOG.info("✅ Setup complete, proceeding to connect.")
    await connect_and_start_weather()


async def connect_and_start_weather():
    """Connect and start weather services."""
    if not CONFIG.is_configured():
        _LOG.error("Weather not configured, cannot connect")
        await API.set_device_state(DeviceStates.ERROR)
        return
    _LOG.info("Setting up weather services...")
    try:
        if await setup_weather_services():
            await asyncio.sleep(0.5)
            await API.set_device_state(DeviceStates.CONNECTED)
            _LOG.info("✅ Device state set to CONNECTED")
        else:
            await API.set_device_state(DeviceStates.ERROR)
    except Exception as e:
        _LOG.error(f"❌ Failed to setup weather services: {e}")
        await API.set_device_state(DeviceStates.ERROR)


@API.listens_to(Events.CONNECT)
async def on_connect() -> None:
    """Called when remote connects via WebSocket."""
    _LOG.info("Remote connected via WebSocket - confirming device state")
    if WEATHER_CLIENT and WEATHER_ENTITY:
        await API.set_device_state(DeviceStates.CONNECTED)
        if WEATHER_ENTITY:
            await WEATHER_ENTITY.update_weather()
    else:
        await connect_and_start_weather()


@API.listens_to(Events.DISCONNECT)
async def on_disconnect() -> None:
    _LOG.info("Remote disconnected")


@API.listens_to(Events.ENTER_STANDBY)
async def on_enter_standby() -> None:
    global UPDATE_TASK
    _LOG.info("Remote entered standby - pausing updates")
    if UPDATE_TASK and not UPDATE_TASK.done():
        UPDATE_TASK.cancel()


@API.listens_to(Events.EXIT_STANDBY)
async def on_exit_standby() -> None:
    _LOG.info("Remote exited standby - resuming updates")
    if WEATHER_ENTITY:
        await WEATHER_ENTITY.update_weather()
        start_weather_updates()


@API.listens_to(Events.SUBSCRIBE_ENTITIES)
async def on_subscribe_entities(entity_ids: list[str]) -> None:
    if WEATHER_ENTITY and WEATHER_ENTITY.id in entity_ids:
        _LOG.info("UI subscribed to our entity. Moving to configured list and starting updates.")
        API.configured_entities.add(WEATHER_ENTITY)
        start_weather_updates()


async def handle_setup(request: ucapi.SetupDriver) -> ucapi.SetupAction:
    """Handle setup process."""
    _LOG.info(f"Handling setup request: {type(request).__name__}")

    if isinstance(request, ucapi.DriverSetupRequest):
        if request.setup_data and "location" in request.setup_data:
            location = request.setup_data.get("location", "").strip()
            
            # *** THE FIX: ***
            # Check the value correctly, handling both boolean False and string "false"
            use_celsius_value = request.setup_data.get("use_celsius", False)
            use_celsius = str(use_celsius_value).lower() == 'true'

            temperature_unit = "celsius" if use_celsius else "fahrenheit"
            if location:
                _LOG.info(f"Processing location from setup_data: {location}, unit: {temperature_unit}")
                try:
                    latitude, longitude, location_name = await WeatherClient.geocode_location(location)
                    test_client = WeatherClient(latitude, longitude, temperature_unit)
                    test_data = await test_client.get_current_weather()
                    await test_client.close()
                    if not test_data: raise Exception("Unable to fetch weather data for this location")
                    
                    CONFIG.set_location(location, latitude, longitude, location_name, temperature_unit)
                    await CONFIG.save()
                    loop.create_task(on_setup_complete())
                    return ucapi.SetupComplete()
                except Exception as e:
                    _LOG.error(f"Setup failed: {e}")
                    return ucapi.SetupError(str(e))

    if isinstance(request, ucapi.UserDataResponse):
        # This case is unlikely to be used now but is fixed for completeness
        location = request.input_values.get("location", "").strip()
        
        # *** THE FIX: ***
        # Apply the same robust check here
        use_celsius_value = request.input_values.get("use_celsius", False)
        use_celsius = str(use_celsius_value).lower() == 'true'

        temperature_unit = "celsius" if use_celsius else "fahrenheit"
        if not location:
            return ucapi.SetupError("Location cannot be empty")
        
        try:
            # This logic is now redundant as driver.json handles all setup.
            # It's kept as a fallback but should ideally not be reached.
            latitude, longitude, location_name = await WeatherClient.geocode_location(location)
            CONFIG.set_location(location, latitude, longitude, location_name, temperature_unit)
            await CONFIG.save()
            loop.create_task(on_setup_complete())
            return ucapi.SetupComplete()
        except Exception as e:
            return ucapi.SetupError(str(e))

    if isinstance(request, ucapi.AbortDriverSetup):
        _LOG.info("Setup aborted by user")
        return ucapi.SetupError(IntegrationSetupError.USER_CANCELLED)

    return ucapi.SetupError(IntegrationSetupError.OTHER)


async def main():
    """Main entry point."""
    global CONFIG
    _LOG.info("🚀 Weather Driver starting...")
    await CONFIG.load()
    driver_path = str(Path(__file__).resolve().parent.parent / "driver.json")
    await API.init(driver_path, handle_setup)
    _LOG.info("Weather Driver is up and discoverable.")
    if CONFIG.is_configured():
        _LOG.info("Complete configuration found, attempting auto-connection...")
        await connect_and_start_weather()
    else:
        _LOG.info("Incomplete configuration, requiring setup.")
        await API.set_device_state(DeviceStates.DISCONNECTED)


if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
        loop.run_forever()
    except KeyboardInterrupt:
        _LOG.info("Driver stopped by user.")
    finally:
        if UPDATE_TASK: UPDATE_TASK.cancel()
        if WEATHER_CLIENT: loop.run_until_complete(WEATHER_CLIENT.close())
        loop.close()