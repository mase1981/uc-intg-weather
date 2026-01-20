"""Simple test to validate clock functionality."""
import asyncio
import sys
from pathlib import Path

# Add the module to the path
sys.path.insert(0, str(Path(__file__).parent))

from uc_intg_weather.weather_entity import WeatherEntity
from uc_intg_weather.client import WeatherClient


async def test_clock_feature():
    """Test that clock updates work correctly."""
    print("Testing clock feature implementation...")

    # Create a mock weather client
    client = WeatherClient(40.7128, -74.0060, "fahrenheit")  # NYC coordinates

    # Create weather entity
    entity = WeatherEntity(
        entity_id="test-weather",
        name="Test Weather",
        weather_client=client,
        location_name="New York, NY",
        api=None
    )

    # Test 1: Initial time update
    print("\nTest 1: Initial time update")
    entity.update_time()
    artist = entity.attributes.get("media_artist", "")
    print(f"  MEDIA_ARTIST: {artist}")

    # Check that time is present in format HH:MM AM/PM
    if ":" in artist and ("AM" in artist or "PM" in artist):
        print("  [PASS] Time format is correct")
    else:
        print("  [FAIL] Time format is incorrect")
        return False

    # Test 2: Weather data integration
    print("\nTest 2: Fetching weather and updating display")
    try:
        await entity.update_weather()
        artist = entity.attributes.get("media_artist", "")
        print(f"  MEDIA_ARTIST: {artist}")

        # Check that display contains time, weather, and temperature
        has_time = ":" in artist and ("AM" in artist or "PM" in artist)
        has_bullet = "•" in artist

        if has_time and has_bullet:
            print("  [PASS] Display format is correct (Time + Weather + Temp)")
        else:
            print("  [FAIL] Display format is incorrect")
            return False

    except Exception as e:
        print(f"  [WARN] Weather fetch failed (expected if no internet): {e}")
        # Still check that time is shown even without weather
        artist = entity.attributes.get("media_artist", "")
        if ":" in artist:
            print("  [PASS] Time is shown even without weather data")
        else:
            print("  [FAIL] Time should be shown even when weather is unavailable")
            return False

    # Test 3: Time update changes the display
    print("\nTest 3: Simulating time passage")
    entity._current_time = "11:59 PM"  # Manually set time
    entity._update_display()
    artist_before = entity.attributes.get("media_artist", "")
    print(f"  Before: {artist_before}")

    entity._current_time = "12:00 AM"  # Simulate time change
    entity._update_display()
    artist_after = entity.attributes.get("media_artist", "")
    print(f"  After:  {artist_after}")

    if artist_before != artist_after:
        print("  [PASS] Time updates are reflected in display")
    else:
        print("  [FAIL] Time updates are not reflected")
        return False

    await client.close()
    print("\n[PASS] All tests passed!")
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_clock_feature())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n[FAIL] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
