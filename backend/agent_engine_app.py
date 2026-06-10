# =============================================================================
# Agent Engine Entrypoint
#
# This module exports a deployment-safe ADK `root_agent` for Google Agent
# Runtime / Agent Engine. It intentionally avoids importing ShiftIQ's local
# `agents.*` package at module import time because Agent Engine unpickles the
# agent object in a managed runtime. Instead, this managed root agent uses the
# deployed Cloud Run API as its live tool backend.
#
# The full web Manager Chat still uses the richer local agent team and MCP
# toolset. This file gives the official managed-agent submission a clean ADK
# root that can answer using live ShiftIQ endpoints.
#
# Main responsibilities:
# - Export `root_agent` for Agent Engine.
# - Use Gemini through Vertex AI via ADK.
# - Provide cloud-safe function tools that call the deployed ShiftIQ backend.
# - Keep the managed agent independent of local file paths and SQLite state.
# =============================================================================

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from google.adk.agents import LlmAgent


DEFAULT_BACKEND_URL = "https://shiftiq-backend-y5d7huc3pq-uc.a.run.app"
DEFAULT_MODEL_NAME = "gemini-2.5-flash-lite"


def _backend_url() -> str:
    return os.getenv("SHIFTIQ_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


def _get_json(path: str) -> dict:
    url = f"{_backend_url()}{path}"
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def get_shift_iq_health() -> dict:
    """Check the deployed ShiftIQ backend health."""
    return _get_json("/health")


def get_shift_iq_labor_summary() -> dict:
    """Return current labor cost summary from the deployed ShiftIQ backend."""
    return _get_json("/labor/summary")


def get_shift_iq_weather_staffing() -> dict:
    """Return weather-adjusted staffing recommendations from the deployed backend."""
    return _get_json("/forecast/weather-aware")


def search_shift_iq_policy(query: str) -> dict:
    """Search ShiftIQ policy/RAG knowledge through the deployed backend."""
    encoded = urllib.parse.quote(str(query or ""))
    return _get_json(f"/knowledge/search?q={encoded}")


def get_shift_iq_schedule() -> dict:
    """Return the current generated schedule from the deployed backend."""
    return _get_json("/schedule/current")


root_agent = LlmAgent(
    model=os.getenv("GOOGLE_ADK_MODEL", DEFAULT_MODEL_NAME),
    name="shiftiq_agent_engine_orchestrator",
    description="Managed ADK orchestrator for ShiftIQ labor, weather staffing, policy retrieval, and schedule context.",
    instruction=(
        "You are ShiftIQ's managed Agent Engine orchestrator. Use the provided tools to answer from the deployed "
        "ShiftIQ backend instead of guessing. For labor, weather, schedule, or policy questions, call the relevant "
        "tool and cite the source values. For risky actions, recommend using the web app Agent Actions approval page."
    ),
    tools=[
        get_shift_iq_health,
        get_shift_iq_labor_summary,
        get_shift_iq_weather_staffing,
        search_shift_iq_policy,
        get_shift_iq_schedule,
    ],
)
