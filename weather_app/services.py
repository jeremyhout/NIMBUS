
import httpx
from datetime import date as _date, datetime, timezone
from .errors import ValidationError, UpstreamError
from timezone_client import get_timezone_client


USER_AGENT = {"User-Agent": "SE-WeatherApp/1.0 (class project)"}


def get_timezone_display(lat: float, lon: float) -> str:
    """
    Get timezone abbreviation for display (e.g., 'EST', 'PST').
    Returns empty string if timezone service is unavailable.
    """
    try:
        client = get_timezone_client()
        result = client.get_timezone(lat, lon)
        if result and result.get('abbreviation'):
            return result['abbreviation']
    except Exception as e:
        # Silently fail - timezone is optional
        pass
    return ""

async def geocode_city(city: str):
    """Return up to 5 candidate places with state/admin1 so users can disambiguate."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city, "count": 5}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params, headers=USER_AGENT)
            r.raise_for_status()
            data = r.json()
            results = data.get("results") or []
            if not results:
                raise ValidationError("City not found. Please check the spelling.")

            matches = []
            for res in results:
                matches.append({
                    "name": res.get("name"),
                    "admin1": res.get("admin1"),                # state/region
                    "country": res.get("country"),
                    "country_code": res.get("country_code"),
                    "lat": res.get("latitude"),
                    "lon": res.get("longitude"),
                })
            return matches
    except httpx.HTTPError as e:
        raise UpstreamError(f"Geocoding failed: {e}")

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

async def fetch_hourly_24(lat: float, lon: float):
    """
    Return the next ~24 hours of temperature and precipitation probability,
    starting from the current time in the location's timezone.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability",
        "timezone": "auto",
        "forecast_hours": 24,  # Get next 24 hours from current time
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(OPEN_METEO, params=params)
            r.raise_for_status()
            j = r.json()
    except Exception as e:
        raise UpstreamError(f"Forecast provider error: {e}")
    
    hourly = (j or {}).get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    pops  = hourly.get("precipitation_probability") or []
    
    out = []
    count = min(24, len(times))
    
    for i in range(count):
        time_str = times[i]
        
        try:
            dt = datetime.fromisoformat(time_str)
        except Exception:
            dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
        
        hour_label = dt.strftime("%I %p").lstrip("0")
        
        out.append({
            "time": time_str,
            "hour": hour_label,
            "temp_c": temps[i] if i < len(temps) else None,
            "pop": pops[i] if i < len(pops) else None,
        })
    
    # Get timezone abbreviation
    tz_abbr = get_timezone_display(lat, lon)
    
    return {
        "hourly": out,
        "timezone": tz_abbr
    }

async def fetch_current_weather(lat: float, lon: float):
    """
    Fetch the current weather from Open-Meteo with timezone auto-detection.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            j = r.json()
            cw = j.get("current_weather") or {}
            
            # Get timezone abbreviation
            tz_abbr = get_timezone_display(lat, lon)
            
            return {
                "temperature_c": cw.get("temperature"),
                "windspeed": cw.get("windspeed"),
                "weathercode": cw.get("weathercode"),
                "time": cw.get("time"),
                "timezone": tz_abbr  # Add timezone to response
            }
    except httpx.HTTPError as e:
        raise UpstreamError(f"Weather provider error: {e}")


async def fetch_5day_forecast(lat: float, lon: float):
    """
    Return five daily entries with local-date strings and precomputed weekday labels.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": 5,
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(OPEN_METEO, params=params)
            r.raise_for_status()
            j = r.json()
    except Exception as e:
        raise UpstreamError(f"Forecast provider error: {e}")

    daily = (j or {}).get("daily") or {}
    times = daily.get("time") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    pops = daily.get("precipitation_probability_max") or []

    out = []
    for i in range(min(5, len(times))):
        ds = times[i]
        try:
            weekday = _date.fromisoformat(ds).strftime("%a")
        except Exception:
            weekday = ""
        out.append({
            "date": ds,
            "weekday": weekday,
            "temp_max_c": tmax[i] if i < len(tmax) else None,
            "temp_min_c": tmin[i] if i < len(tmin) else None,
            "pop": pops[i] if i < len(pops) else None,
        })
    
    # Get timezone abbreviation
    tz_abbr = get_timezone_display(lat, lon)
    
    return {
        "forecast": out,
        "timezone": tz_abbr  # Add timezone to response
    }
