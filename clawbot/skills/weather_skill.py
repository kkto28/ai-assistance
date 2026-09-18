"""BBC Weather skill for retrieving current conditions from a location page."""
from __future__ import annotations

import json
import re
from html import unescape
from urllib.error import URLError
from urllib.parse import quote_plus, unquote
from urllib.request import Request, urlopen

from skills import tool

_BBC_WEATHER_BASE = "https://www.bbc.com/weather"
_FORECAST_STATE = re.compile(
    r'<script[^>]+type=["\']application/json["\'][^>]+'
    r'data-state-id=(?:["\']forecast["\']|forecast)[^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_LOCATION_NAME_ATTRIBUTE = re.compile(
    r'<html[^>]+data-location-name=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_SEARCH_RESULT = re.compile(
    r'<a[^>]+href=["\']/weather/(\d+)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG = re.compile(r"<[^>]+>")
_LOCATION_INPUT = re.compile(r"^[A-Za-z][A-Za-z .'-]*$")


def _resolve_location(location: str) -> dict[str, str]:
    location = _normalize_location(location)
    if location.isdigit():
        return {"id": location, "name": "Unknown location", "container": ""}

    search_url = f"{_BBC_WEATHER_BASE}/search?s={quote_plus(location)}"
    results = []
    for location_id, raw_label in _SEARCH_RESULT.findall(_fetch(search_url)):
        label = " ".join(unescape(_HTML_TAG.sub("", raw_label)).split())
        parts = [part.strip() for part in label.split(",", 1)]
        results.append(
            {
                "id": location_id,
                "name": parts[0],
                "container": parts[1] if len(parts) == 2 else "",
            }
        )
    if not results:
        raise ValueError(f"No BBC Weather location found for '{location}'")

    requested = location.casefold()
    results.sort(
        key=lambda result: (
            result["name"].casefold() != requested,
            "airport" in result["name"].casefold(),
        )
    )
    return results[0]


def _normalize_location(location: str) -> str:
    if not isinstance(location, str):
        raise ValueError("location must be a string")
    normalized = " ".join(location.split())
    if not normalized:
        raise ValueError("location must not be empty")
    if normalized.isdigit():
        return normalized
    if not _LOCATION_INPUT.fullmatch(normalized):
        raise ValueError("location must contain letters, spaces, apostrophes, or hyphens")
    return normalized.title()


def _fetch(url: str) -> str:
    request = Request(
        url,
        headers={
            "Accept": "text/html",
            "User-Agent": "Clawbot weather skill",
        },
    )
    with urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8")


def _parse_forecast(html: str) -> dict:
    state_match = _FORECAST_STATE.search(html)
    if not state_match:
        raise ValueError("BBC Weather forecast data was not found")

    try:
        state = json.loads(state_match.group(1))
        detailed = state["data"]["forecasts"][0]["detailed"]
        report = detailed["reports"][0]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("BBC Weather forecast data had an unexpected format") from exc

    location_match = _LOCATION_NAME_ATTRIBUTE.search(html)
    location = (
        unquote(location_match.group(1)) if location_match else "Unknown location"
    )
    fields = {
        "location": location,
        "updated": report.get("lastUpdated", detailed.get("lastUpdated", "unknown")),
        "temperature_c": report.get("temperatureC"),
        "feels_like_c": report.get("feelsLikeTemperatureC"),
        "condition": report.get("weatherTypeText", "Unknown"),
        "description": report.get("enhancedWeatherDescription", ""),
        "humidity": report.get("humidity"),
        "wind_speed_mph": report.get("windSpeedMph"),
        "wind": report.get("windDescription", ""),
        "precipitation": report.get("precipitationProbabilityText", ""),
    }
    if fields["temperature_c"] is None:
        raise ValueError("BBC Weather forecast did not include a temperature")
    return fields


def _format_forecast(forecast: dict, source_url: str) -> str:
    lines = [
        f"{forecast['location']} weather",
        (
            f"Temperature: {forecast['temperature_c']}°C "
            f"(feels like {forecast['feels_like_c']}°C)"
        ),
        f"Condition: {forecast['condition']}",
    ]
    if forecast["description"]:
        lines.append(f"Summary: {forecast['description']}")
    if forecast["humidity"] is not None:
        lines.append(f"Humidity: {forecast['humidity']}%")
    if forecast["wind_speed_mph"] is not None:
        lines.append(f"Wind: {forecast['wind_speed_mph']} mph")
    if forecast["wind"]:
        lines.append(f"Wind detail: {forecast['wind']}")
    if forecast["precipitation"]:
        lines.append(f"Precipitation: {forecast['precipitation']}")
    lines.append(f"Updated: {forecast['updated']}")
    lines.append(f"Source: {source_url}")
    return "\n".join(lines)


def _format_error(prefix: str, exc: Exception) -> str:
    if isinstance(exc, URLError) and getattr(exc, "reason", None):
        exc = exc.reason
    return f"Error: {prefix}: {exc}"


@tool(
    name="resolve_weather_location",
    description=(
        "Resolve a city or place name to the closest main BBC Weather "
        "location and numeric location ID."
    ),
)
def resolve_weather_location(location: str) -> str:
    try:
        result = _resolve_location(location)
        label = result["name"]
        if result["container"]:
            label += f", {result['container']}"
        return f"{label} — BBC Weather location ID: {result['id']}"
    except (URLError, ValueError, TimeoutError, OSError) as exc:
        return _format_error("could not resolve BBC Weather location", exc)


def _fetch_weather_by_id(location_id: str) -> str:
    source_url = f"{_BBC_WEATHER_BASE}/{location_id}"
    forecast = _parse_forecast(_fetch(source_url))
    return _format_forecast(forecast, source_url)


@tool(
    name="get_weather_by_location_id",
    description=(
        "Get the latest current weather using a numeric BBC Weather "
        "location ID returned by resolve_weather_location."
    ),
)
def get_weather_by_location_id(location_id: str) -> str:
    if not isinstance(location_id, str) or not location_id.strip().isdigit():
        return "Error: location_id must be a numeric BBC Weather location ID."
    try:
        return _fetch_weather_by_id(location_id.strip())
    except (URLError, ValueError, TimeoutError, OSError) as exc:
        return _format_error("could not fetch BBC Weather", exc)
