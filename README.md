# Weather Display Integration for Unfolded Circle Remote 2/3

Display real-time weather conditions with a **live clock** and beautiful contextual icons directly on your Unfolded Circle Remote 2 or Remote 3. Features **real-time clock display**, **day/night icon variants**, **comprehensive weather coverage**, and **automatic updates** powered by the free Open-Meteo API.

![Weather](https://img.shields.io/badge/Weather-Display-orange)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-weather?style=flat-square)](https://github.com/mase1981/uc-intg-weather/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-weather?style=flat-square)](https://github.com/mase1981/uc-intg-weather/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://unfolded.community/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-weather/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)


## Features

This integration displays current weather conditions with a live clock on your Unfolded Circle Remote using the free Open-Meteo API, delivering seamless integration with beautiful, modern 3D-styled icons that automatically adapt to day and night conditions.

---
## ❤️ Support Development ❤️

If you find this integration useful, consider supporting development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️
---

### 🌤️ **Weather Display Features**

#### **Live Clock Display**
- **Real-Time Clock** - Updates every minute with current time, **only while the tile is on screen**
- **12-Hour Format** - Displays time as HH:MM AM/PM
- **No API Calls** - Uses local system time for the clock
- **Always Visible** - Shows even when weather data unavailable
- **Smart Display** - Time + Weather + Temperature format
- **Battery Aware** - Stops when the tile is not displayed and during standby; resumes automatically

#### **Real-Time Weather Information**
- **Current Temperature** - Fahrenheit or Celsius display
- **Weather Description** - Human-readable conditions
- **Location Display** - Shows configured location name
- **Weather Icons** - Beautiful 3D-styled icons with day/night variants
- **Smart Updates** - Battery-efficient update intervals (30min-4hr based on time of day)

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
- **Direct Coordinates** - Latitude/Longitude input (e.g., 51.5074, -0.1278)
- **Automatic Geocoding** - Converts location to coordinates
- **Timezone Detection** - Automatically determines local timezone

### **API Requirements**

- **Protocol**: Open-Meteo Weather API
- **API Key**: Not required (free service)
- **Coverage**: Global weather data
- **Update Frequency**: Hourly automatic refresh
- **Data Points**: Temperature, weather code, day/night status
- **Reliability**: High uptime and performance

### **Network Requirements**

- **Internet Access** - Integration requires internet connection
- **HTTPS Protocol** - Open-Meteo API (HTTPS)
- **Firewall** - Must allow HTTPS traffic
- **Geocoding** - Location converted to coordinates automatically

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
      - UC_INTEGRATION_INTERFACE=0.0.0.0
      - PYTHONPATH=/app
    restart: unless-stopped
```

**Docker Run:**
```bash
docker run -d --name uc-weather --restart unless-stopped --network host -v weather-config:/data -e UC_CONFIG_HOME=/data -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 -e PYTHONPATH=/app ghcr.io/mase1981/uc-intg-weather:latest
```

## Configuration

### Step 1: Setup Integration

1. After installation, go to **Settings** → **Integrations**
2. The Weather Display integration should appear in **Available Integrations**
3. Click **"Configure"** to begin setup

### Step 2: Enter Location

**Location Format Options:**

**Option A: Location String (Automatic Geocoding)**

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

**Option B: Direct Coordinates (Advanced)**

For precise location control, you can enter coordinates directly:

**Latitude/Longitude:**
- Leave "Location" field empty
- Enter **Latitude**: `-90` to `90` (positive = North, negative = South)
- Enter **Longitude**: `-180` to `180` (positive = East, negative = West)
- Example: Latitude `51.5074`, Longitude `-0.1278` (London)
- Example: Latitude `40.7128`, Longitude `-74.0060` (New York)
- Optional: Enter a display name for your location

**Why use coordinates?**
- Exact location precision (useful for rural areas)
- Works with Open-Meteo API URL format
- No ambiguity in location lookup
- Ideal for locations with non-standard names

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

The integration creates a single media player entity that displays weather information with live clock:

**Entity Display:**
- **Media Title**: Location name (e.g., "New York, NY")
- **Media Artist**: Time + Weather + Temperature (e.g., "02:30 PM • Partly cloudy • 72.5°F")
- **Media Album**: Weather description (e.g., "Partly cloudy")
- **Media Image**: Weather-appropriate icon

**Clock Feature:**
- Updates every 60 seconds while the tile is displayed
- Uses local system time (no API calls for the clock)
- Stops when the tile is not on screen and during remote standby
- Resumes automatically when displayed again or on wake

**Entity States:**
- **On**: Weather data available and current
- **Unavailable**: Tile not displayed, in standby, or API connection issue

### Weather Icon Reference

| Icon | Conditions | Day/Night |
|------|-----------|-----------|
| Sun | Clear sky | Day only |
| Moon | Clear sky | Night only |
| Sun-Cloud | Partly cloudy | Day only |
| Moon-Cloud | Partly cloudy | Night only |
| Cloud | Overcast | Both |
| Fog | Fog conditions | Both |
| Drizzle | Light drizzle | Both |
| Rain-Light | Light rain | Both |
| Rain | Moderate rain | Both |
| Rain-Heavy | Heavy rain | Both |
| Freezing-Rain | Freezing rain/drizzle | Both |
| Snow-Light | Light snow | Both |
| Snow | Moderate snow | Both |
| Snow-Heavy | Heavy snow | Both |
| Thunderstorm | Thunderstorms | Both |
| Hail | Hail conditions | Both |

### Update Frequency

**Display lifecycle (battery):**
- Both the clock and weather updates run **only while the weather tile is on screen**
- When you navigate away, stop the activity, or the Remote enters standby, all updates **stop**
- Everything resumes automatically when the tile is displayed again or the Remote wakes

**Clock Updates:**
- **Real-Time**: Updates every 60 seconds while displayed
- **Battery Efficient**: No API calls, uses local time only

**Weather Updates:**
- **Smart Intervals**: Battery-efficient scheduling based on time of day
  - Night (11PM-6AM): Every 4 hours
  - Peak times (6-9AM, 5-8PM): Every 30 minutes
  - Regular hours: Every hour
- **On Demand**: Power on (ON command) triggers an immediate refresh
- **Reliable**: Stays available and shows "Weather unavailable" on transient API errors

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
- **UC Community Forum**: [General discussion and support](https://unfolded.community/)
- **Discord**: [Join the UC Discord](https://discord.gg/zGVYf58)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)
- **Open-Meteo**: [Weather API Documentation](https://open-meteo.com/)

---

**Made with ❤️ for the Unfolded Circle Community**

**Thank You**: Meir Miyara
