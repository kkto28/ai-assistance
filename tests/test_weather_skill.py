import json
import os
from urllib.error import URLError
from urllib.parse import quote_plus

import pytest

from skills import registry
from skills import weather_skill


def forecast_html(report=None, location="London"):
    report = report or {
        "lastUpdated": "2026-09-18T22:00:00+01:00",
        "temperatureC": 17,
        "feelsLikeTemperatureC": 18,
        "weatherTypeText": "Light Cloud",
        "enhancedWeatherDescription": "Light cloud and a gentle breeze",
        "humidity": 73,
        "windSpeedMph": 11,
        "windDescription": "A gentle breeze from the south-west",
        "precipitationProbabilityText": "Precipitation is not expected",
    }
    state = {"data": {"forecasts": [{"detailed": {"reports": [report]}}]}}
    return (
        f'<html data-location-name="{location}">'
        '<script type="application/json" data-state-id="forecast">'
        f"{json.dumps(state)}"
        "</script></html>"
    )


def test_parse_forecast_returns_latest_current_report():
    result = weather_skill._parse_forecast(forecast_html())

    assert result == {
        "location": "London",
        "updated": "2026-09-18T22:00:00+01:00",
        "temperature_c": 17,
        "feels_like_c": 18,
        "condition": "Light Cloud",
        "description": "Light cloud and a gentle breeze",
        "humidity": 73,
        "wind_speed_mph": 11,
        "wind": "A gentle breeze from the south-west",
        "precipitation": "Precipitation is not expected",
    }


@pytest.mark.parametrize(
    "location, location_id",
    [("Example City", "2648579"), ("Harbor Town", "1819729")],
)
def test_resolve_location_name_uses_first_bbc_search_result(
    monkeypatch, location, location_id
):
    search_html = (
        f'<a href="/weather/{location_id}">{location}</a>'
        '<a href="/weather/9999999">Another place</a>'
    )
    requested = []
    monkeypatch.setattr(
        weather_skill,
        "_fetch",
        lambda url: requested.append(url) or search_html,
    )

    assert weather_skill._resolve_location(location)["id"] == location_id
    assert requested == [
        f"https://www.bbc.com/weather/search?s={quote_plus(location)}"
    ]


def test_resolve_location_prefers_exact_main_city_over_other_matches(monkeypatch):
    search_html = (
        '<a href="/weather/6296626">Example City Airport, Example County</a>'
        '<a href="/weather/2648579">Example City, Example County</a>'
        '<a href="/weather/2640060">Port Example, Example County</a>'
    )
    monkeypatch.setattr(weather_skill, "_fetch", lambda _url: search_html)

    assert weather_skill._resolve_location("Example City") == {
        "id": "2648579",
        "name": "Example City",
        "container": "Example County",
    }


def test_resolve_weather_location_tool_returns_location_id(monkeypatch):
    monkeypatch.setattr(
        weather_skill,
        "_resolve_location",
        lambda _location: {
            "id": "2648579",
            "name": "Example City",
            "container": "Example County",
        },
    )

    assert weather_skill.resolve_weather_location("example city") == (
        "Example City, Example County — BBC Weather location ID: 2648579"
    )


def test_get_weather_by_location_id_rejects_names(monkeypatch):
    result = weather_skill.get_weather_by_location_id("Example City")

    assert result == "Error: location_id must be a numeric BBC Weather location ID."


def test_get_weather_by_location_id_fetches_forecast(monkeypatch):
    monkeypatch.setattr(
        weather_skill,
        "_fetch",
        lambda url: forecast_html(location="Example City"),
    )

    result = weather_skill.get_weather_by_location_id("2648579")

    assert "Example City weather" in result
    assert "Source: https://www.bbc.com/weather/2648579" in result


def test_resolve_location_name_reports_no_bbc_match(monkeypatch):
    monkeypatch.setattr(weather_skill, "_fetch", lambda _url: "<html></html>")

    with pytest.raises(ValueError, match="No BBC Weather location found"):
        weather_skill._resolve_location("Atlantis")


@pytest.mark.parametrize(
    "location, expected",
    [
        ("Example City", "Example City"),
        ("example city", "Example City"),
        (" harbor   town ", "Harbor Town"),
        ("ABC", "Abc"),
        ("abc", "Abc"),
    ],
)
def test_normalize_location_accepts_names_and_aliases(location, expected):
    assert weather_skill._normalize_location(location) == expected


@pytest.mark.parametrize("location", ["", "   ", "ABC!!!"])
def test_normalize_location_rejects_invalid_names(location):
    with pytest.raises(ValueError, match="location"):
        weather_skill._normalize_location(location)


@pytest.mark.parametrize("location", ["example city", "abc"])
def test_resolve_location_uses_normalized_lookup_name(monkeypatch, location):
    requested = []
    monkeypatch.setattr(
        weather_skill,
        "_fetch",
        lambda url: requested.append(url)
        or '<a href="/weather/2648579">Example City</a>',
    )

    assert weather_skill._resolve_location(location)["id"] == "2648579"
    expected_search = "Example City" if location == "example city" else "Abc"
    assert requested == [
        f"https://www.bbc.com/weather/search?s={quote_plus(expected_search)}"
    ]


def test_get_weather_reports_network_errors(monkeypatch):
    def fail(_url):
        raise URLError("offline")

    monkeypatch.setattr(weather_skill, "_fetch", fail)

    assert weather_skill.get_weather_by_location_id("2643743") == (
        "Error: could not fetch BBC Weather: offline"
    )


def test_weather_skill_registers_resolution_and_id_tools():
    assert registry.get("resolve_weather_location").func is (
        weather_skill.resolve_weather_location
    )
    assert registry.get("get_weather_by_location_id").func is (
        weather_skill.get_weather_by_location_id
    )


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_WEATHER_TESTS") != "1",
    reason="Live BBC Weather tests are opt-in",
)
def test_live_bbc_weather_response():
    result = weather_skill.get_weather_by_location_id("2643743")

    assert result.startswith("London weather\n")
    assert "Temperature:" in result
    assert "Condition:" in result
    assert "Source: https://www.bbc.com/weather/2643743" in result


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_WEATHER_TESTS") != "1",
    reason="Live BBC Weather tests are opt-in",
)
def test_live_bbc_location_resolution():
    result = weather_skill.resolve_weather_location("London")

    assert "BBC Weather location ID:" in result
    location_id = result.rsplit(":", 1)[-1].strip()
    assert location_id.isdigit()
