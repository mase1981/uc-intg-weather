# Weather Display Integration for Unfolded Circle Remote 2/3

Display real-time weather conditions with beautiful, contextual icons directly on your Unfolded Circle Remote 2 or Remote 3 screen. Features **day/night icon variants**, **comprehensive weather coverage**, and **automatic hourly updates** powered by the free Open-Meteo API.

![Weather](https://img.shields.io/badge/Weather-Display-orange)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-weather?style=flat-square)](https://github.com/mase1981/uc-intg-weather/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-weather?style=flat-square)](https://github.com/mase1981/uc-intg-weather/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://community.unfoldedcircle.com/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-weather/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)

## Features

This integration displays current weather conditions on your Unfolded Circle Remote using the free Open-Meteo API. Weather information is presented as a media player entity with beautiful, modern 3D-styled icons that automatically adapt to day and night conditions.

---
## ❤️ Support Development

If you find this integration useful, consider supporting development and show your support:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️
---

### 🌤️ **Weather Display Features**

#### **Real-Time Weather Information**
- **Current Temperature** - Fahrenheit or Celsius display
- **Weather Description** - Human-readable conditions
- **Location Display** - Shows configured location name
- **Weather Icons** - Beautiful 3D-styled icons with day/night variants
- **Automatic Updates** - Refreshes every hour

#### **Comprehensive Weather Coverage**
16 weather condition icons covering:
- **Clear Conditions** - Day sun and night moon icons
- **Partly Cloudy** - Contextual day/night cloud variants
- **Overcast & Fog** - Full cloud coverage and fog conditions
- **Rain Family** - Drizzle, light rain, moderate rain, heavy rain, freezing rain
- **Snow Family** - Light, moderate, and heavy snow conditions
- **Severe Weather** - Thunderstorms and hail

#### **Day/Night Contextual Icons**
- **Daytime Icons** - Bright sun-based icons during daylight hours
- **Nighttime Icons** - Moon and stars for evening/night conditions
- **Automatic Switching** - Icons change based on sunrise/sunset times
- **Local Timezone** - Respects your location's time zone

#### **Temperature Display Options**
- **Fahrenheit (°F)** - Default temperature unit
- **Celsius (°C)** - Optional metric display
- **Decimal Precision** - Shows one decimal place for accuracy

### 🌍 **Location Support**

- **ZIP/Postal Codes** - US and international postal codes
- **City, State Format** - "New York, NY" or "Los Angeles, CA"
- **International Cities** - "London, UK" or "Paris, France"
- **Automatic Geocoding** - Converts location to coordinates
- **Timezone Detection** - Automatically determines local timezone

### 📊 **Weather Data Provider**

- **API**: Open-Meteo (free, no API key required)
- **Coverage**: Global weather data
- **Update Frequency**: Hourly automatic refresh
- **Data Points**: Temperature, weather code, day/night status
- **Reliability**: High uptime and performance
- **Privacy**: No API key, no tracking

### 🎨 **Visual Design**

- **Modern 3D Icons** - Professional gradient styling with depth
- **High Resolution** - 256x256 PNG icons optimized for remote display
- **Vibrant Colors** - Weather-appropriate color palettes
- **Clean Layout** - Location as title, temperature as artist, description as album
- **Icon Quality** - Optimized for UC Remote LED screen

## Installation

### Option 1: Remote Web Interface (Recommended)
1. Navigate to the [**Releases**](https://github.com/mase1981/uc-intg-weather/releases) page
2. Download the latest `uc-intg-weather-<version>-aarch64.tar.gz` file
3. Open your remote's web interface (`http://your-remote-ip`)
4. Go to **Settings** → **Integrations** → **Add Integration**
5. Click **Upload** and select the downloaded `.tar.gz` file

### Option 2: Docker (Advanced Users)

The integration is available as a pre-built Docker image from GitHub Container Registry:

**Image**: `ghcr.io/mase1981/uc-intg-weather:latest`

**Docker Compose:**
```yaml
services:
  uc-intg-weather:
    image: ghcr.io/mase1981/uc-intg-weather:latest
    container_name: uc-intg-weather
    network_mode: host
    volumes:
      - </local/path>:/data
    environment:
      - UC_CONFIG_HOME=/data
      - UC_INTEGRATION_HTTP_PORT=9090
    restart: unless-stopped
```

**Docker Run:**
```bash
docker run -d --name uc-weather --restart unless-stopped --network host -v weather-config:/app/config -e UC_CONFIG_HOME=/app/config -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 -e PYTHONPATH=/app ghcr.io/mase1981/uc-intg-weather:latest
```

## Configuration

### Step 1: Setup Integration

1. After installation, go to **Settings** → **Integrations**
2. The Weather Display integration should appear in **Available Integrations**
3. Click **"Configure"** to begin setup

### Step 2: Enter Location

**Location Format Options:**

**US ZIP Code:**
- Format: `12345` or `12345-6789`
- Example: `10001` (New York City)
- Example: `90210` (Beverly Hills)

**City, State:**
- Format: `City, State` or `City, ST`
- Example: `New York, NY`
- Example: `Los Angeles, California`

**International:**
- Format: `City, Country`
- Example: `London, UK`
- Example: `Paris, France`
- Example: `Tokyo, Japan`

### Step 3: Choose Temperature Unit

- **Fahrenheit (°F)** - Default, US standard
- **Celsius (°C)** - Metric, international standard

### Step 4: Complete Setup

1. Integration verifies location with Open-Meteo API
2. Tests geocoding and weather data retrieval
3. Creates weather display entity
4. Begins hourly automatic updates

**Setup Validation:**
- Location geocoded successfully
- Initial weather data retrieved
- Weather icons cached locally
- Entity registered with remote

## Using the Integration

### Weather Display Entity

The integration creates a single media player entity that displays weather information:

**Entity Display:**
- **Media Title**: Location name (e.g., "New York, NY")
- **Media Artist**: Current temperature (e.g., "72.5°F")
- **Media Album**: Weather description (e.g., "Partly cloudy")
- **Media Image**: Weather-appropriate icon

**Entity States:**
- **Playing**: Weather data available and current
- **Unavailable**: Integration or API connection issue

### Weather Icon Reference

| Icon | Conditions | Day/Night |
|------|-----------|-----------|
| ☀️ **Sun** | Clear sky | Day only |
| 🌙 **Moon** | Clear sky | Night only |
| ⛅ **Sun-Cloud** | Partly cloudy | Day only |
| 🌙☁️ **Moon-Cloud** | Partly cloudy | Night only |
| ☁️ **Cloud** | Overcast | Both |
| 🌫️ **Fog** | Fog conditions | Both |
| 🌦️ **Drizzle** | Light drizzle | Both |
| 🌧️ **Rain-Light** | Light rain | Both |
| 🌧️ **Rain** | Moderate rain | Both |
| ⛈️ **Rain-Heavy** | Heavy rain | Both |
| 🧊 **Freezing-Rain** | Freezing rain/drizzle | Both |
| 🌨️ **Snow-Light** | Light snow | Both |
| ❄️ **Snow** | Moderate snow | Both |
| ❄️❄️ **Snow-Heavy** | Heavy snow | Both |
| ⚡ **Thunderstorm** | Thunderstorms | Both |
| 🧊 **Hail** | Hail conditions | Both |

### WMO Weather Code Coverage

The integration supports all standard WMO (World Meteorological Organization) weather codes:

**Clear & Cloudy (0-3):**
- 0, 1: Clear/Mainly clear
- 2: Partly cloudy
- 3: Overcast

**Fog (45-48):**
- 45, 48: Fog conditions

**Drizzle (51-57):**
- 51, 53, 55: Light to dense drizzle
- 56, 57: Freezing drizzle

**Rain (61-67, 80-82):**
- 61, 80: Slight rain/showers
- 63, 81: Moderate rain/showers
- 65, 82: Heavy/violent rain
- 66, 67: Freezing rain

**Snow (71-77, 85-86):**
- 71, 85: Slight snow
- 73, 86: Moderate snow
- 75, 77: Heavy snow/grains

**Hail (87-88):**
- 87, 88: Slight/heavy hail

**Thunderstorm (95-99):**
- 95, 96, 99: Thunderstorm (with/without hail)

### Update Frequency

- **Automatic**: Updates every hour
- **On Demand**: Remote power on/wake triggers immediate update
- **Manual**: Restart integration to force update
- **Reliable**: Automatic retry on API failures

## Troubleshooting

### Common Issues

**1. Setup fails with "Location not found"**
- **Solution**: Verify location format (ZIP or "City, State")
- **Try**: Different format (state abbreviation vs. full name)
- **Check**: Spelling of city and state names

**2. Weather data not updating**
- **Check**: Network connectivity to open-meteo.com
- **Verify**: Remote can reach internet
- **Review**: Integration logs for API errors
- **Test**: Manual remote restart

**3. Icons not displaying**
- **Verify**: Icon files in `uc_intg_weather/icons/` directory
- **Check**: Icon files in `cache/` directory
- **Confirm**: File permissions are correct
- **Validate**: PNG files are not corrupted

**4. Wrong temperature unit**
- **Fix**: Reconfigure integration with correct unit
- **Note**: Changes require integration restart

**5. Integration unavailable after reboot**
- **Note**: This integration includes reboot survival
- **Check**: Entity should automatically restore
- **Verify**: Configuration file exists
- **Review**: Logs for initialization errors

### Debug Mode

**Enable debug logging:**
1. Access integration configuration directory
2. Check logs for detailed error messages
3. Look for API connection errors
4. Verify geocoding responses

**Common log messages:**
- "Weather data retrieved successfully" - Normal operation
- "Failed to fetch weather data" - API connection issue
- "Unknown weather code" - Unmapped WMO code (uses fallback)
- "Icon not found" - Missing icon file

### API Issues

**Open-Meteo API Problems:**
- **Rate Limiting**: Free API has generous limits
- **Service Down**: Check https://open-meteo.com/
- **Network Issues**: Verify internet connectivity
- **Geocoding Fails**: Try different location format

## Development

### Local Development Setup

**Prerequisites:**
- Python 3.11+
- Virtual environment
- Git

**Setup Steps:**

1. **Clone repository**
   ```bash
   git clone https://github.com/mase1981/uc-intg-weather.git
   cd uc-intg-weather
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   export UC_CONFIG_HOME=./config
   export UC_INTEGRATION_HTTP_PORT=9090
   export UC_DISABLE_MDNS_PUBLISH=true
   ```

4. **Run in VS Code**
   - Open project in VS Code
   - Use provided launch configuration
   - Press F5 to start debugging

### Project Structure

```
uc-intg-weather/
├── uc_intg_weather/           # Main package
│   ├── __init__.py            # Package info with dynamic version
│   ├── client.py              # Open-Meteo API client
│   ├── config.py              # Configuration management
│   ├── driver.py              # Main integration driver
│   ├── weather_entity.py      # Weather media player entity
│   ├── setup.py               # Setup flow handler
│   └── icons/                 # Weather icon assets
│       ├── sun.png            # Day clear icon
│       ├── moon.png           # Night clear icon
│       ├── sun-cloud.png      # Day partly cloudy
│       ├── moon-cloud.png     # Night partly cloudy
│       ├── cloud.png          # Overcast
│       ├── fog.png            # Fog
│       ├── drizzle.png        # Drizzle
│       ├── rain-light.png     # Light rain
│       ├── rain.png           # Moderate rain
│       ├── rain-heavy.png     # Heavy rain
│       ├── freezing-rain.png  # Freezing rain
│       ├── snow-light.png     # Light snow
│       ├── snow.png           # Moderate snow
│       ├── snow-heavy.png     # Heavy snow
│       ├── thunderstorm.png   # Thunderstorm
│       └── hail.png           # Hail
├── cache/                     # Cached weather icons
├── .github/workflows/         # GitHub Actions CI/CD
│   └── build.yml              # Automated build pipeline
├── .vscode/                   # VS Code configuration
│   └── launch.json            # Debug configuration
├── docker-compose.yml         # Docker deployment
├── Dockerfile                 # Container build instructions
├── driver.json                # Integration metadata
├── requirements.txt           # Dependencies
├── pyproject.toml             # Python project config
└── README.md                  # This file
```

### Key Implementation Details

#### **Open-Meteo API Integration**
- Free API, no authentication required
- Global weather coverage
- Hourly data updates
- High reliability and uptime

#### **API Request Format**
```python
{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "current": ["temperature_2m", "weather_code", "is_day"],
    "temperature_unit": "fahrenheit",  # or "celsius"
    "timezone": "auto"
}
```

#### **API Response Format**
```json
{
    "current": {
        "temperature_2m": 72.5,
        "weather_code": 2,
        "is_day": 1
    }
}
```

#### **Icon Selection Logic**
```python
def _get_weather_icon_url(weather_code: int, is_day: int) -> str:
    # Day/night variants for clear and partly cloudy
    if weather_code in [0, 1]:
        return "sun.png" if is_day else "moon.png"
    elif weather_code == 2:
        return "sun-cloud.png" if is_day else "moon-cloud.png"
    
    # Universal icons for other conditions
    # ... comprehensive WMO code mapping
```

#### **Reboot Survival Pattern**
```python
# Pre-initialize if config exists
async def main():
    config = WeatherConfig()
    if config.is_configured():
        loop.create_task(_initialize_entities())

# Reload config on reconnect
async def on_connect():
    config.reload_from_disk()
    if config.is_configured() and not entities_ready:
        await _initialize_entities()

# Race condition protection
async def on_subscribe_entities(entity_ids):
    if not entities_ready:
        await _initialize_entities()
```

#### **Wake-Up Error Handling**
```python
# WiFi stabilization after wake
try:
    response = await fetch_weather()
except ClientOSError:
    await asyncio.sleep(0.5)  # Wait for WiFi
    response = await fetch_weather()  # Retry once
```

### Testing

**Manual Testing:**
1. Configure with test location
2. Verify initial weather display
3. Wait for hourly update
4. Test remote reboot survival
5. Verify day/night icon switching

**Location Testing:**
```python
# Test various location formats
locations = [
    "10001",              # ZIP code
    "New York, NY",       # City, State
    "London, UK",         # International
    "90210-1234"          # ZIP+4
]
```

**Icon Testing:**
```python
# Test all weather codes
test_codes = [0, 2, 3, 45, 51, 61, 71, 87, 95]
for code in test_codes:
    icon = get_weather_icon(code, is_day=1)
    verify_icon_exists(icon)
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test thoroughly
4. Follow code style guidelines (header comments only)
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Style

- Follow PEP 8 Python conventions
- Use type hints for all functions
- Async/await for all I/O operations
- Comprehensive docstrings
- Descriptive variable names
- Header comments only (no inline comments)

## Credits

- **Developer**: Meir Miyara
- **Weather Data**: Open-Meteo (free global weather API)
- **Unfolded Circle**: Remote 2/3 integration framework (ucapi)
- **Icons**: Custom 3D-styled weather icons
- **Community**: Testing and feedback from UC community

## License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0) - see LICENSE file for details.

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-weather/issues)
- **UC Community Forum**: [General discussion and support](https://community.unfoldedcircle.com/)
- **Discord**: [Join the UC Discord](https://discord.gg/zGVYf58)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)
- **Open-Meteo**: [Weather API Documentation](https://open-meteo.com/)

---

**Made with ❤️ for the Unfolded Circle Community** 

**Thank You**: Meir Miyara