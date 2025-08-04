# Weather Integration for Unfolded Circle Remote

This integration displays current weather conditions on your Unfolded Circle Remote 3 using the Open-Meteo API. Weather information is presented as a media player entity with beautiful weather icons.

## Features

- 🌤️ Real-time weather display with beautiful icons
- 📍 Support for ZIP codes and "City, State" location formats
- 🔄 Automatic updates every hour
- 🖼️ Weather-appropriate icons (sun, clouds, rain, thunderstorms, etc.)
- 🌡️ Temperature, weather description, and location display
- 🔌 Easy setup through the Remote's web configurator

## Weather Information Display

The integration uses the media player entity format to display:
- **Media Title**: Location name (e.g., "New York, NY")
- **Media Artist**: Current temperature (e.g., "72.5°F")
- **Media Album**: Weather description (e.g., "Partly cloudy")
- **Media Image**: Weather-appropriate icon

## Installation

### Method 1: Tar.gz Package (Recommended)

1. Download the latest `uc-intg-weather.tar.gz` from the [Releases](../../releases) page
2. Upload via the Remote's web configurator
3. Follow the setup process to configure your location

### Method 2: Docker

```bash
# Using docker-compose
docker-compose up -d

# Or using Docker directly
docker run -d \
  --name uc-intg-weather \
  --network host \
  -v ./config:/app/config \
  -e UC_CONFIG_HOME=/app/config \
  -e UC_INTEGRATION_HTTP_PORT=9094 \
  uc-intg-weather:latest
```

## Configuration

During setup, you'll be prompted to enter your location in one of these formats:

- **ZIP Code**: `12345` or `12345-6789`
- **City, State**: `New York, NY` or `Los Angeles, CA`
- **International**: `London, UK` or `Paris, France`

The integration will automatically:
1. Geocode your location to get coordinates
2. Test the weather API connection
3. Cache weather icons locally
4. Begin hourly weather updates

## Weather Icons

The integration includes beautiful weather icons for:
- ☀️ Clear sky / Sunny
- ⛅ Partly cloudy
- ☁️ Cloudy / Overcast
- 🌫️ Fog
- 🌦️ Light rain / Drizzle
- 🌧️ Rain
- ⛈️ Thunderstorms
- 🌨️ Snow

## Development

### Prerequisites

- Python 3.10+
- Virtual environment (recommended)
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mase1981/uc-intg-weather.git
   cd uc-intg-weather
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run in VS Code**
   - Open the project in VS Code
   - Use the provided launch configuration
   - Press F5 to start debugging

4. **Environment Variables** (for testing)
   ```bash
   export UC_CONFIG_HOME=./config
   export UC_INTEGRATION_HTTP_PORT=9094
   export UC_DISABLE_MDNS_PUBLISH=true
   ```

### Project Structure

```
uc-intg-weather/
├── uc_intg_weather/           # Main integration package
│   ├── __init__.py           # Package initialization
│   ├── driver.py             # Main integration driver
│   ├── client.py             # Open-Meteo API client
│   ├── weather_entity.py     # Weather media player entity
│   ├── config.py             # Configuration management
│   └── icons/                # Weather icons directory
│       ├── sun.png
│       ├── cloud.png
│       ├── rain.png
│       └── ...
├── cache/                    # Cached weather icons
├── config/                   # Runtime configuration
├── .vscode/
│   └── launch.json           # VS Code debug configuration
├── .github/
│   └── workflows/
│       └── build.yml         # GitHub Actions build
├── driver.json               # Integration metadata
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker build instructions
├── docker-compose.yml        # Docker Compose configuration
└── README.md                 # This file
```

### API Usage

The integration uses the free [Open-Meteo API](https://open-meteo.com/) which provides:
- No API key required
- High reliability and performance
- Detailed weather codes for accurate icon selection
- Global coverage

## Troubleshooting

### Common Issues

1. **Setup fails with "Location not found"**
   - Verify location format (ZIP code or "City, State")
   - Try a different format (e.g., use state abbreviation)

2. **Weather data not updating**
   - Check network connectivity
   - Verify the Remote can reach open-meteo.com
   - Check integration logs

3. **Icons not displaying**
   - Ensure icon files exist in `uc_intg_weather/icons/`
   - Check file permissions
   - Verify file paths are correct

### Debug Mode

Enable debug logging by setting the log level in `driver.py`:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

### Log Files

Logs are written to:
- Console output during development
- System logs when running as service
- Docker logs: `docker logs uc-intg-weather`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly on your Remote
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Weather data provided by [Open-Meteo](https://open-meteo.com/)
- Built for [Unfolded Circle Remote](https://www.unfoldedcircle.com/)
- Weather icons designed for optimal remote display

## Support

- 🐛 **Issues**: [GitHub Issues](../../issues)
- 💬 **Discussions**: [GitHub Discussions](../../discussions)
- 📧 **Contact**: [Your Email](mailto:your.email@example.com)

---

**Enjoy beautiful weather displays on your Unfolded Circle Remote!** 🌤️ Thank You: Meir  Miyara