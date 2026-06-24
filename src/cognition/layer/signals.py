import logging
import psutil
import requests

logger = logging.getLogger("packy.signals")

def read_cpu():
    """Read current CPU percentage (0-100).

    Returns:
        float: CPU percentage clamped to 0-100
    """
    try:
        return psutil.cpu_percent(interval=0.1)
    except Exception as e:
        logger.warning("Failed to read CPU: %s", e)
        return 0.0

def read_weather(api_key, location):
    """Read weather data from OpenWeatherMap API.

    Args:
        api_key: OpenWeatherMap API key (or None to skip)
        location: City name or location string

    Returns:
        Tuple of (temp_celsius or None, description_string)
    """
    if not api_key:
        return None, "unknown"

    try:
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?q={location}&appid={api_key}&units=metric"
        )
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            logger.warning("Weather API returned status %d", r.status_code)
            return None, "unknown"
        data = r.json()
        temp = data.get("main", {}).get("temp")
        desc = data.get("weather", [{}])[0].get("description", "unknown")
        return temp, desc
    except requests.RequestException as e:
        logger.warning("Weather API request failed: %s", e)
        return None, "unknown"
    except (KeyError, ValueError) as e:
        logger.warning("Failed to parse weather response: %s", e)
        return None, "unknown"
    except Exception as e:
        logger.exception("Unexpected error reading weather: %s", e)
        return None, "unknown"
