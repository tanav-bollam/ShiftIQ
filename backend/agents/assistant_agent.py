# =============================================================================
# Manager Assistant Agent
#
# This file powers the Manager Chat page. It turns the rest of the ShiftIQ data
# model into concise, manager-friendly answers about sales trends, labor cost,
# staffing risk, employee details, and schedule recommendations. The agent uses
# a hybrid strategy: if GOOGLE_API_KEY is configured, it creates a Google ADK
# Gemini agent with live ShiftIQ tools; otherwise, it falls back to deterministic
# local responses so the hackathon demo always works without external services.
#
# Main responsibilities:
# - Build answers from live forecast, busiest-period, overstaffing, labor, and
#   employee data.
# - Expose ShiftIQ data functions as Google ADK tools so Manager Chat can reason
#   over current schedule, labor, employee, forecast, call-out, and threshold
#   state instead of answering from stale hardcoded values.
# - Provide reliable canned-but-data-grounded fallback answers for common demo
#   questions such as labor reduction, busiest hours, Sarah's status, and the
#   Saturday forecast.
# - Keep chat responses specific and practical by referencing real values from
#   the CSV-backed agents and the current in-memory schedule.
#
# This agent does not mutate schedules or data. It reads from other agents and
# explains what it finds in plain English.
# =============================================================================

import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
from uuid import uuid4

from agents.forecast_agent import forecast_next_week
from agents.insight_agent import get_busiest_periods, get_daily_revenue, get_hourly_heatmap, get_overstaffing_alerts, get_top_items
from agents.scheduler_agent import generate_schedule, get_current_schedule, labor_summary
from agents.data_agent import load_employees
from agents.staffing_agent import get_staffing_thresholds
from agents.shift_request_agent import list_shift_requests


APP_NAME = "shiftiq_manager_chat"
USER_ID = "manager"
DEFAULT_MODEL_NAME = "gemini-3.1-flash-lite"


def _load_local_env():
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")


def _model_name():
    return os.getenv("GOOGLE_ADK_MODEL", DEFAULT_MODEL_NAME)


def _uses_vertex_ai():
    return os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() == "true"


def _json_safe(value):
    return json.loads(json.dumps(value, default=str))


def get_shiftiq_overview() -> dict:
    """Return a compact overview of live ShiftIQ operating data."""
    labor = labor_summary()
    forecast = forecast_next_week()
    current = get_current_schedule()
    return {
        "labor": labor,
        "forecast": forecast,
        "schedule_mode": current.get("mode", "block"),
        "schedule_blocks": len(current.get("schedule", [])),
        "hours_by_employee": current.get("hours_by_employee", {}),
        "busiest_periods": get_busiest_periods(5),
        "overstaffing_alerts": get_overstaffing_alerts(),
        "staffing_thresholds": get_staffing_thresholds(),
    }


def get_sales_insights() -> dict:
    """Return sales insight data including daily revenue, heatmap, top items, and busiest hours."""
    return {
        "daily_revenue": get_daily_revenue(),
        "busiest_periods": get_busiest_periods(8),
        "top_items": get_top_items(),
        "hourly_heatmap_sample": get_hourly_heatmap()[:40],
        "overstaffing_alerts": get_overstaffing_alerts(),
    }


def get_employee_profile(name_or_id: str) -> dict:
    """Look up one employee by name or id and include their scheduled hours."""
    employees = load_employees().to_dict(orient="records")
    current = get_current_schedule()
    needle = str(name_or_id).lower().strip()
    match = next(
        (
            emp
            for emp in employees
            if str(emp["id"]) == needle or needle in str(emp["name"]).lower()
        ),
        None,
    )
    if not match:
        return {"error": f"No employee found for {name_or_id}."}
    emp_id = int(match["id"])
    match["scheduled_hours"] = current.get("hours_by_employee", {}).get(emp_id, 0)
    match["assigned_shifts"] = [
        {
            "day": shift["day"],
            "shift": shift["shift"],
            "time": shift["time"],
            "role": assignment["role"],
        }
        for shift in current.get("schedule", [])
        for assignment in shift.get("assigned", [])
        if assignment["employee_id"] == emp_id
    ]
    return _json_safe(match)


def get_schedule_summary() -> dict:
    """Return the current schedule, explanations, labor summary, and shift requests."""
    return {
        "schedule": get_current_schedule(),
        "labor": labor_summary(),
        "shift_requests": list_shift_requests(),
    }


def generate_shift_schedule(mode: str = "block") -> dict:
    """Generate a ShiftIQ schedule in block or flexible mode and return the updated summary."""
    normalized = "flexible" if str(mode).lower() == "flexible" else "block"
    schedule = generate_schedule(mode=normalized)
    return {
        "generated_mode": normalized,
        "schedule_count": len(schedule.get("schedule", [])),
        "schedule": schedule,
        "labor": labor_summary(),
    }


def _context_prompt() -> str:
    overview = get_shiftiq_overview()
    employees = load_employees().head(18).to_dict(orient="records")
    return (
        "You are ShiftIQ, an AI operations manager for a small food/retail business. "
        "Answer manager questions using live ShiftIQ tool data. Be concise, specific, and practical. "
        "Use exact numbers when available. If a user asks about a schedule action, explain the tradeoff before recommending it. "
        "Do not invent employees, sales numbers, or schedule facts.\n\n"
        f"Current live snapshot: {json.dumps(_json_safe(overview), ensure_ascii=False)}\n"
        f"Employee roster snapshot: {json.dumps(_json_safe(employees), ensure_ascii=False)}"
    )


async def _run_adk_chat(message: str, history: list | None = None) -> str:
    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    agent = LlmAgent(
        model=_model_name(),
        name="shiftiq_manager_agent",
        description="Answers ShiftIQ manager questions using live operations tools.",
        instruction=_context_prompt(),
        tools=[
            get_shiftiq_overview,
            get_sales_insights,
            get_employee_profile,
            get_schedule_summary,
            generate_shift_schedule,
        ],
    )
    session_service = InMemorySessionService()
    session_id = f"manager-{uuid4().hex}"
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

    history_text = ""
    if history:
        recent = history[-6:]
        history_text = "\nRecent chat history:\n" + "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}" for item in recent
        )
    user_content = types.Content(role="user", parts=[types.Part(text=f"{history_text}\nManager question: {message}")])
    final_response = ""
    async for event in runner.run_async(user_id=USER_ID, session_id=session_id, new_message=user_content):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text or final_response
    return final_response or _fallback(message)


def _fallback(message: str):
    text = message.lower()
    forecast = forecast_next_week()
    busiest = get_busiest_periods(3)
    alerts = get_overstaffing_alerts()
    labor = labor_summary()
    employees = load_employees().to_dict(orient="records")

    if "reduce" in text or "$200" in text or "labor" in text:
        alert = alerts[0] if alerts else None
        if alert:
            return (
                f"Start with {alert['day']} at {alert['hour']}:00. Revenue averages ${alert['revenue']:.0f}/hr "
                f"and the modeled labor load is {alert['labor_pct']}%, above the 30% target. "
                f"Removing one low-demand coverage block is the cleanest path toward a $200 weekly labor reduction."
            )
        return f"Current weekly labor is {labor['weekly']['labor_pct']}% of forecast revenue, with ${labor['weekly']['labor_cost']:.0f} scheduled."
    if "busy" in text or "busiest" in text:
        top = busiest[0]
        return f"Your busiest period is {top['day']} at {top['hour']}:00, averaging ${top['revenue']:.0f}/hr. Keep full cashier and closer coverage there."
    if "overstaff" in text:
        if not alerts:
            return "I do not see an overstaffing alert above the 30% labor target in the current data."
        return "The clearest overstaffing risks are " + ", ".join(
            f"{a['day']} {a['hour']}:00 at {a['labor_pct']}%" for a in alerts[:3]
        ) + "."
    if "sarah" in text:
        sarah = next((emp for emp in employees if emp["name"].startswith("Sarah")), None)
        if sarah:
            hours = get_current_schedule().get("hours_by_employee", {}).get(int(sarah["id"]), 0)
            return f"Sarah K. is a high-priority closer/cashier with a {sarah['max_hours']}h cap. She currently has {hours} scheduled hours and {sarah['callouts_this_month']} call-out cover this month."
    if "saturday" in text:
        sat = next(item for item in forecast if item["day"] == "Saturday")
        return f"Saturday forecast is ${sat['predicted_revenue']:.0f} with {sat['confidence_pct']}% confidence. Plan for about {sat['staff_needed']} staff across peak coverage."
    return (
        f"Weekly labor is currently {labor['weekly']['labor_pct']}% against a 30% target. "
        "Ask about busiest hours, overstaffing, Saturday forecast, Sarah, or labor reduction for a specific recommendation."
    )


def chat(message: str, history: list | None = None):
    _load_local_env()
    if not _uses_vertex_ai() and not os.getenv("GOOGLE_API_KEY"):
        return _fallback(message)

    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return asyncio.run(_run_adk_chat(message, history))
    except Exception:
        return _fallback(message)
