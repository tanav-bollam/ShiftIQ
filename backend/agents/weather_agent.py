# =============================================================================
# Weather-Aware Staffing Agent
#
# This file adds external-context grounding to ShiftIQ's demand planning. Food
# and dessert shops are sensitive to weather: hot afternoons can lift ice cream
# demand, while heavy rain can suppress walk-in traffic. This agent fetches a
# seven-day weather outlook when possible and falls back to deterministic demo
# weather when external network access is unavailable.
#
# Main responsibilities:
# - Fetch local daily weather from Open-Meteo using store latitude/longitude.
# - Convert weather into explainable demand multipliers.
# - Adjust the existing POS-based forecast with weather context.
# - Recommend extra or reduced staffing based on weather-adjusted demand.
#
# This gives the ADK/MCP story a real external-context tool while keeping the
# core schedule generator stable.
# =============================================================================

from __future__ import annotations

import os
from datetime import date, timedelta

import httpx

from agents.data_agent import DAY_ORDER
from agents.forecast_agent import forecast_next_week
from agents.persistence_agent import log_audit


DEFAULT_LAT = float(os.getenv("STORE_LAT", "40.7128"))
DEFAULT_LON = float(os.getenv("STORE_LON", "-74.0060"))


def _fallback_weather():
    demo = [
        {"high_f": 72, "precip_in": 0.02, "condition": "Mild"},
        {"high_f": 68, "precip_in": 0.28, "condition": "Rain risk"},
        {"high_f": 74, "precip_in": 0.04, "condition": "Mild"},
        {"high_f": 79, "precip_in": 0.0, "condition": "Warm"},
        {"high_f": 84, "precip_in": 0.0, "condition": "Hot"},
        {"high_f": 88, "precip_in": 0.01, "condition": "Hot weekend"},
        {"high_f": 81, "precip_in": 0.08, "condition": "Warm"},
    ]
    today = date.today()
    return [
        {
            "date": (today + timedelta(days=index)).isoformat(),
            "day": day,
            **demo[index],
            "source": "demo-fallback",
        }
        for index, day in enumerate(DAY_ORDER)
    ]


def get_weather_forecast(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON):
    """Return a seven-day weather forecast for staffing context."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,precipitation_sum",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "timezone": "auto",
        "forecast_days": 7,
    }
    try:
        response = httpx.get(url, params=params, timeout=4)
        response.raise_for_status()
        data = response.json()["daily"]
        rows = []
        for index, day in enumerate(DAY_ORDER):
            high = round(float(data["temperature_2m_max"][index]), 1)
            precip = round(float(data["precipitation_sum"][index]), 2)
            if precip >= 0.35:
                condition = "Heavy rain"
            elif precip >= 0.12:
                condition = "Rain risk"
            elif high >= 85:
                condition = "Hot"
            elif high >= 78:
                condition = "Warm"
            else:
                condition = "Mild"
            rows.append(
                {
                    "date": data["time"][index],
                    "day": day,
                    "high_f": high,
                    "precip_in": precip,
                    "condition": condition,
                    "source": "open-meteo",
                }
            )
        return rows
    except Exception as exc:
        log_audit("weather", "fetch_forecast", "fallback", {"error": str(exc)}, actor="weather_agent")
        return _fallback_weather()


def weather_demand_multiplier(weather_row: dict):
    high = float(weather_row["high_f"])
    precip = float(weather_row["precip_in"])
    multiplier = 1.0
    reasons = []

    if high >= 88:
        multiplier += 0.14
        reasons.append("very hot weather tends to lift cold-item demand")
    elif high >= 82:
        multiplier += 0.09
        reasons.append("hot weather tends to lift dessert traffic")
    elif high >= 76:
        multiplier += 0.04
        reasons.append("warm weather slightly lifts demand")

    if precip >= 0.35:
        multiplier -= 0.12
        reasons.append("heavy rain can reduce walk-in traffic")
    elif precip >= 0.12:
        multiplier -= 0.06
        reasons.append("rain risk can soften walk-in traffic")

    multiplier = max(0.78, min(1.22, multiplier))
    return round(multiplier, 3), reasons or ["weather impact is neutral"]


def weather_adjusted_forecast():
    """Return forecast rows adjusted by seven-day weather context."""
    base = forecast_next_week()
    weather = {row["day"]: row for row in get_weather_forecast()}
    adjusted = []
    for row in base:
        weather_row = weather[row["day"]]
        multiplier, reasons = weather_demand_multiplier(weather_row)
        adjusted_revenue = round(row["predicted_revenue"] * multiplier, 2)
        staff_needed = max(2, round(adjusted_revenue / 950))
        weather_staff_delta = int(staff_needed - row["staff_needed"])
        adjusted.append(
            {
                **row,
                "weather": weather_row,
                "weather_multiplier": multiplier,
                "weather_reasons": reasons,
                "weather_adjusted_revenue": adjusted_revenue,
                "weather_adjusted_staff_needed": int(staff_needed),
                "weather_staff_delta": weather_staff_delta,
            }
        )
    log_audit("weather", "weather_adjusted_forecast", "ok", {"days": len(adjusted)}, actor="weather_agent")
    return adjusted


def weather_staffing_recommendations():
    """Return concise staffing recommendations from weather-adjusted demand."""
    rows = weather_adjusted_forecast()
    recommendations = []
    for row in rows:
        delta = row["weather_staff_delta"]
        if delta > 0:
            action = f"Add {delta} extra coverage slot{'s' if delta > 1 else ''}."
        elif delta < 0:
            action = f"Consider reducing {-delta} coverage slot{'s' if delta < -1 else ''}."
        else:
            action = "Keep baseline staffing."
        recommendations.append(
            {
                "day": row["day"],
                "condition": row["weather"]["condition"],
                "high_f": row["weather"]["high_f"],
                "precip_in": row["weather"]["precip_in"],
                "baseline_staff": row["staff_needed"],
                "weather_adjusted_staff": row["weather_adjusted_staff_needed"],
                "action": action,
                "reason": "; ".join(row["weather_reasons"]),
            }
        )
    return recommendations

