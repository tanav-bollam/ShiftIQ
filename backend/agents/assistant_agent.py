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
# - Execute explicit manager commands for supported operations, such as switching
#   the current schedule between shift-block and flexible-demand modes.
# - Keep chat responses specific and practical by referencing real values from
#   the CSV-backed agents and the current in-memory schedule.
#
# Most questions are read-only. Explicit action requests mutate only the same
# in-memory demo state that the Schedule page already uses.
# =============================================================================

import asyncio
import csv
import contextlib
import io
import json
import os
from pathlib import Path

from agents.forecast_agent import forecast_next_week
from agents.insight_agent import get_busiest_periods, get_daily_revenue, get_hourly_heatmap, get_overstaffing_alerts, get_top_items
from agents.messaging_agent import find_backups
from agents.scheduler_agent import generate_schedule, get_current_schedule as scheduler_current_schedule, labor_summary
from agents.data_agent import load_employees
from agents.staffing_agent import get_staffing_thresholds
from agents.shift_request_agent import list_shift_requests
from agents import state


APP_NAME = "shiftiq_manager_chat"
USER_ID = "manager"
DEFAULT_MODEL_NAME = "gemini-3.1-flash-lite"
DEFAULT_AGENT_ID = "orchestrator"


AGENT_PROFILES = {
    "orchestrator": {
        "label": "Core Orchestrator",
        "description": "General ShiftIQ manager assistant that coordinates sales, labor, schedule, and coverage tools.",
        "focus": (
            "You are the Core Orchestrator. Answer broad manager questions and decide which ShiftIQ tools to consult. "
            "When useful, synthesize schedule, labor, employee, and coverage data into one practical answer."
        ),
        "tools": "all",
    },
    "tool_calling": {
        "label": "Tool Calling Agent",
        "description": "Direct access to live ShiftIQ data and app actions.",
        "focus": (
            "You are the Tool Calling Agent. Prefer calling tools and reporting exact values from live ShiftIQ data. "
            "Keep interpretation light and make it clear which tool data supports the answer."
        ),
        "tools": "data",
    },
    "schedule_explanation": {
        "label": "Schedule Explanation Agent",
        "description": "Explains assignments, role coverage, and unfilled schedule slots.",
        "focus": (
            "You are the Schedule Explanation Agent. Explain why people were assigned, what constraints mattered, "
            "and where coverage is strong or weak. Use schedule explanations and employee profiles."
        ),
        "tools": "schedule",
    },
    "coverage": {
        "label": "Call-Out & Coverage Agent",
        "description": "Finds backup candidates and explains coverage recommendations.",
        "focus": (
            "You are the Call-Out & Shift Coverage Assistant. Help managers respond to dropped shifts and call-outs. "
            "Rank candidates by availability, skills, remaining hours, priority, and fairness."
        ),
        "tools": "coverage",
    },
    "labor": {
        "label": "Labor Optimization Agent",
        "description": "Finds labor-cost savings and staffing efficiency recommendations.",
        "focus": (
            "You are the Labor Optimization Assistant. Focus on labor percentage, savings opportunities, overstaffing, "
            "and concrete staffing changes. Return dollar estimates when available."
        ),
        "tools": "labor",
    },
    "exports": {
        "label": "Report & Export Agent",
        "description": "Creates downloadable schedule and labor report artifacts.",
        "focus": (
            "You are the Report & Schedule Export Agent. Create CSV or text report artifacts when requested, then "
            "describe what was generated and how the manager can use it."
        ),
        "tools": "exports",
    },
}


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


def _session_service():
    if not hasattr(state, "adk_session_service") or state.adk_session_service is None:
        from google.adk.sessions import InMemorySessionService

        state.adk_session_service = InMemorySessionService()
    return state.adk_session_service


def _artifact_service():
    if not hasattr(state, "adk_artifact_service") or state.adk_artifact_service is None:
        from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService

        state.adk_artifact_service = InMemoryArtifactService()
    return state.adk_artifact_service


def _agent_id(agent: str | None):
    normalized = (agent or DEFAULT_AGENT_ID).strip().lower()
    return normalized if normalized in AGENT_PROFILES else DEFAULT_AGENT_ID


async def _ensure_session(agent_id: str):
    service = _session_service()
    session_id = f"manager-{agent_id}"
    session = await service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)
    if session is None:
        session = await service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
            state={"agent_id": agent_id, "agent_label": AGENT_PROFILES[agent_id]["label"]},
        )
    return session


def _record_agent_event(agent_id: str, event_type: str, detail: dict):
    if not hasattr(state, "adk_agent_events"):
        state.adk_agent_events = []
    state.adk_agent_events.append(
        {
            "agent": agent_id,
            "agent_label": AGENT_PROFILES.get(agent_id, AGENT_PROFILES[DEFAULT_AGENT_ID])["label"],
            "event_type": event_type,
            "detail": _json_safe(detail),
        }
    )
    state.adk_agent_events = state.adk_agent_events[-80:]


def get_shiftiq_overview() -> dict:
    """Return a compact overview of live ShiftIQ operating data."""
    labor = labor_summary()
    forecast = forecast_next_week()
    current = scheduler_current_schedule()
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


def get_labor_summary() -> dict:
    """Return the current daily and weekly labor summary."""
    return labor_summary()


def get_current_schedule() -> dict:
    """Return the current generated schedule and assignment explanations."""
    return scheduler_current_schedule()


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
    current = scheduler_current_schedule()
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
        "schedule": scheduler_current_schedule(),
        "labor": labor_summary(),
        "shift_requests": list_shift_requests(),
    }


def explain_schedule_assignment(name_or_id: str = "", day: str = "", shift_name: str = "") -> dict:
    """Explain why an employee, day, or shift was assigned in the current schedule."""
    current = scheduler_current_schedule()
    if not current.get("schedule"):
        current = generate_schedule()
    needle = str(name_or_id or "").lower().strip()
    day_filter = str(day or "").lower().strip()
    shift_filter = str(shift_name or "").lower().strip()

    matching_shifts = []
    for shift in current.get("schedule", []):
        if day_filter and shift["day"].lower() != day_filter:
            continue
        if shift_filter and shift_filter not in shift["shift"].lower():
            continue
        if needle:
            has_match = any(
                needle in assignment["name"].lower() or str(assignment["employee_id"]) == needle
                for assignment in shift.get("assigned", [])
            )
            if not has_match:
                continue
        matching_shifts.append(shift)

    matching_explanations = []
    for item in current.get("explanations", []):
        if day_filter and item.get("day", "").lower() != day_filter:
            continue
        if shift_filter and shift_filter not in item.get("shift", "").lower():
            continue
        if needle and needle not in str(item.get("employee") or "").lower():
            continue
        matching_explanations.append(item)

    return {
        "mode": current.get("mode"),
        "matching_shifts": matching_shifts[:12],
        "matching_explanations": matching_explanations[:20],
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


def find_backup_candidates(called_out_name_or_id: str, day: str = "", shift_name: str = "") -> dict:
    """Rank backup candidates for a called-out employee and shift."""
    current = scheduler_current_schedule()
    if not current.get("schedule"):
        current = generate_schedule()
    employees = load_employees().to_dict(orient="records")
    needle = str(called_out_name_or_id).lower().strip()
    called_out = next(
        (
            emp
            for emp in employees
            if str(emp["id"]) == needle or needle in emp["name"].lower()
        ),
        None,
    )
    if not called_out:
        return {"status": "error", "message": f"No employee matched {called_out_name_or_id}."}

    target_shift = None
    for shift in current.get("schedule", []):
        if day and shift["day"].lower() != day.lower():
            continue
        if shift_name and shift_name.lower() not in shift["shift"].lower():
            continue
        if any(assignment["employee_id"] == int(called_out["id"]) for assignment in shift.get("assigned", [])):
            target_shift = shift
            break
    if target_shift is None:
        target_shift = next(
            (
                shift
                for shift in current.get("schedule", [])
                if any(assignment["employee_id"] == int(called_out["id"]) for assignment in shift.get("assigned", []))
            ),
            None,
        )
    if target_shift is None:
        return {"status": "error", "message": f"{called_out['name']} is not assigned to a current shift."}

    return find_backups(int(called_out["id"]), target_shift["shift"], target_shift["day"])


def optimize_labor_savings(target_savings: float = 200.0) -> dict:
    """Recommend schedule changes that could reduce labor cost by a target amount."""
    current = scheduler_current_schedule()
    if not current.get("schedule"):
        current = generate_schedule()
    alerts = get_overstaffing_alerts()
    recommendations = []
    running_savings = 0.0

    for shift in sorted(current.get("schedule", []), key=lambda item: item.get("expected_hourly_revenue", 9999)):
        duration = int(shift["time_end"] - shift["time_start"])
        removable = [
            assignment
            for assignment in shift.get("assigned", [])
            if assignment["role"] == "Cashier" or shift.get("extra_dynamic_slots", 0) > 0
        ]
        if not removable:
            continue
        assignment = sorted(removable, key=lambda item: float(item.get("hourly_wage", 0)), reverse=True)[0]
        savings = round(float(assignment["hourly_wage"]) * duration, 2)
        running_savings += savings
        recommendations.append(
            {
                "day": shift["day"],
                "shift": shift["shift"],
                "employee": assignment["name"],
                "role": assignment["role"],
                "estimated_savings": savings,
                "reason": (
                    f"{shift['day']} {shift['shift']} averages ${shift.get('expected_hourly_revenue', 0):.0f}/hour "
                    f"and can be reviewed for one fewer {assignment['role']} slot."
                ),
            }
        )
        if running_savings >= float(target_savings):
            break

    return {
        "target_savings": float(target_savings),
        "estimated_savings": round(running_savings, 2),
        "recommendations": recommendations,
        "overstaffing_alerts": alerts[:5],
        "labor": labor_summary(),
    }


def _schedule_csv_text():
    current = scheduler_current_schedule()
    if not current.get("schedule"):
        current = generate_schedule()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["day", "shift", "time", "employee", "role", "hourly_wage"])
    for shift in current.get("schedule", []):
        for assignment in shift.get("assigned", []):
            writer.writerow(
                [
                    shift["day"],
                    shift["shift"],
                    shift["time"],
                    assignment["name"],
                    assignment["role"],
                    assignment.get("hourly_wage", ""),
                ]
            )
    return output.getvalue()


def _labor_report_text():
    labor = labor_summary()
    lines = [
        "ShiftIQ Labor Report",
        f"Weekly labor: {labor['weekly']['labor_pct']}% target {labor['weekly']['target_pct']}%",
        f"Weekly labor cost: ${labor['weekly']['labor_cost']}",
        f"Forecast revenue: ${labor['weekly']['revenue']}",
        "",
        "Daily detail:",
    ]
    for day in labor["daily"]:
        lines.append(f"- {day['day']}: ${day['labor_cost']} labor on ${day['revenue']} revenue = {day['labor_pct']}% ({day['status']})")
    return "\n".join(lines)


async def create_report_artifact(kind: str = "weekly_schedule_csv") -> dict:
    """Create a downloadable report artifact for schedule, labor, or staffing recommendations."""
    normalized = str(kind or "weekly_schedule_csv").lower()
    if "labor" in normalized:
        filename = "user:labor-report.txt"
        content = _labor_report_text()
        mime_type = "text/plain"
    elif "recommend" in normalized or "staff" in normalized:
        filename = "user:staffing-recommendations.txt"
        content = json.dumps(_json_safe(optimize_labor_savings(200)), indent=2)
        mime_type = "application/json"
    else:
        filename = "user:weekly-schedule.csv"
        content = _schedule_csv_text()
        mime_type = "text/csv"

    from google.genai import types

    revision = await _artifact_service().save_artifact(
        app_name=APP_NAME,
        user_id=USER_ID,
        filename=filename,
        artifact=types.Part.from_bytes(data=content.encode("utf-8"), mime_type=mime_type),
        custom_metadata={"source": "ShiftIQ Manager Chat", "kind": normalized},
    )
    return {
        "filename": filename,
        "display_name": filename.replace("user:", "", 1),
        "revision": revision,
        "mime_type": mime_type,
        "download_url": f"/chat/artifacts/{filename}",
        "summary": f"Created {filename} as an ADK artifact.",
    }


async def list_report_artifacts() -> list[dict]:
    """List report artifacts created by Manager Chat."""
    keys = await _artifact_service().list_artifact_keys(app_name=APP_NAME, user_id=USER_ID)
    return [{"filename": key, "display_name": key.replace("user:", "", 1), "download_url": f"/chat/artifacts/{key}"} for key in keys]


async def load_report_artifact(filename: str):
    """Load one report artifact by filename."""
    return await _artifact_service().load_artifact(app_name=APP_NAME, user_id=USER_ID, filename=filename)


def _requested_schedule_mode(message: str) -> str | None:
    text = message.lower()
    schedule_terms = ("schedule", "shift", "shifts", "staffing")
    action_terms = ("switch", "change", "convert", "make", "set", "use", "generate", "optimize", "turn")
    has_schedule_context = any(term in text for term in schedule_terms)
    has_action = any(term in text for term in action_terms)
    if not has_schedule_context or not has_action:
        return None
    if "flexible" in text or "demand" in text or "non-block" in text or "not blocked" in text:
        return "flexible"
    if "block" in text or "shift block" in text or "fixed" in text:
        return "block"
    return None


def _requested_artifact_kind(message: str) -> str | None:
    text = message.lower()
    if not any(term in text for term in ("export", "download", "csv", "report", "artifact", "file")):
        return None
    if "labor" in text:
        return "labor_report"
    if "recommend" in text or "staffing" in text:
        return "staffing_recommendations"
    if "schedule" in text or "csv" in text:
        return "weekly_schedule_csv"
    return "weekly_schedule_csv"


def _execute_schedule_mode_change(mode: str) -> str:
    result = generate_schedule(mode=mode)
    labor = labor_summary()
    schedule_count = len(result.get("schedule", []))
    assigned_count = sum(len(shift.get("assigned", [])) for shift in result.get("schedule", []))
    unfilled_count = sum(len(shift.get("unfilled_roles", [])) for shift in result.get("schedule", []))
    label = "flexible demand" if mode == "flexible" else "shift block"
    return (
        f"Done. I switched the schedule to {label} mode and regenerated the week. "
        f"It now has {schedule_count} coverage windows, {assigned_count} assignments, "
        f"and {unfilled_count} unfilled role slots. Weekly labor is "
        f"{labor['weekly']['labor_pct']}% against the {labor['weekly']['target_pct']}% target."
    )


def _execute_artifact_request(kind: str) -> str:
    artifact = asyncio.run(create_report_artifact(kind))
    return (
        f"Done. I created {artifact['display_name']} as an ADK artifact. "
        f"Download it from {artifact['download_url']}."
    )


def _agent_tools(agent_id: str):
    data_tools = [
        get_shiftiq_overview,
        get_labor_summary,
        get_current_schedule,
        get_sales_insights,
        get_employee_profile,
        get_schedule_summary,
        generate_shift_schedule,
    ]
    schedule_tools = [
        get_current_schedule,
        get_employee_profile,
        get_schedule_summary,
        explain_schedule_assignment,
        generate_shift_schedule,
    ]
    coverage_tools = [
        get_current_schedule,
        get_employee_profile,
        find_backup_candidates,
        get_schedule_summary,
    ]
    labor_tools = [
        get_labor_summary,
        get_sales_insights,
        get_current_schedule,
        optimize_labor_savings,
        generate_shift_schedule,
    ]
    export_tools = [
        get_labor_summary,
        get_current_schedule,
        optimize_labor_savings,
        create_report_artifact,
        list_report_artifacts,
    ]
    if agent_id == "tool_calling":
        return data_tools
    if agent_id == "schedule_explanation":
        return schedule_tools
    if agent_id == "coverage":
        return coverage_tools
    if agent_id == "labor":
        return labor_tools
    if agent_id == "exports":
        return export_tools
    return list({tool.__name__: tool for tool in data_tools + schedule_tools + coverage_tools + labor_tools + export_tools}.values())


def _before_tool_callback(tool, args, tool_context):
    agent_id = tool_context.state.get("agent_id", DEFAULT_AGENT_ID)
    _record_agent_event(agent_id, "before_tool", {"tool": tool.name, "args": args})
    return None


def _after_tool_callback(tool, args, tool_context, tool_response):
    agent_id = tool_context.state.get("agent_id", DEFAULT_AGENT_ID)
    _record_agent_event(agent_id, "after_tool", {"tool": tool.name, "result_preview": str(tool_response)[:400]})
    return None


def _after_agent_callback(callback_context):
    agent_id = callback_context.state.get("agent_id", DEFAULT_AGENT_ID)
    _record_agent_event(agent_id, "after_agent", {"message": "Agent run completed"})
    return None


def _context_prompt() -> str:
    overview = get_shiftiq_overview()
    employees = load_employees().head(18).to_dict(orient="records")
    return (
        "You are ShiftIQ, an AI operations manager for a small food/retail business. "
        "Answer manager questions using live ShiftIQ tool data. Be concise, specific, and practical. "
        "Use exact numbers when available. If a user asks about a schedule action, explain the tradeoff before recommending it. "
        "If the user explicitly asks you to switch, generate, optimize, set, or change the schedule mode, call generate_shift_schedule. "
        "Do not invent employees, sales numbers, or schedule facts.\n\n"
        f"Current live snapshot: {json.dumps(_json_safe(overview), ensure_ascii=False)}\n"
        f"Employee roster snapshot: {json.dumps(_json_safe(employees), ensure_ascii=False)}"
    )


def _agent_instruction(agent_id: str) -> str:
    profile = AGENT_PROFILES[agent_id]
    return (
        f"{profile['focus']}\n\n"
        "Agent team structure:\n"
        "- Core Orchestrator handles general manager conversation and coordinates the specialist tools.\n"
        "- Tool Calling Agent fetches exact live ShiftIQ data and performs allowed app actions.\n"
        "- Schedule Explanation Agent explains assignments, role coverage, and unfilled slots.\n"
        "- Call-Out & Coverage Agent ranks replacement candidates for dropped shifts.\n"
        "- Labor Optimization Agent recommends concrete cost-saving moves.\n"
        "- Report & Export Agent creates ADK artifacts for schedule and labor reports.\n\n"
        f"{_context_prompt()}"
    )


async def _run_adk_chat(message: str, history: list | None = None, agent: str | None = None) -> str:
    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.genai import types

    agent_id = _agent_id(agent)
    profile = AGENT_PROFILES[agent_id]
    agent = LlmAgent(
        model=_model_name(),
        name=f"shiftiq_{agent_id}_agent",
        description=profile["description"],
        instruction=_agent_instruction(agent_id),
        tools=_agent_tools(agent_id),
        before_tool_callback=_before_tool_callback,
        after_tool_callback=_after_tool_callback,
        after_agent_callback=_after_agent_callback,
    )
    session = await _ensure_session(agent_id)
    session_service = _session_service()
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

    history_text = ""
    if history:
        recent = history[-6:]
        history_text = "\nRecent chat history:\n" + "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}" for item in recent
        )
    user_content = types.Content(role="user", parts=[types.Part(text=f"{history_text}\nManager question: {message}")])
    final_response = ""
    async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=user_content):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text or final_response
    return final_response or _fallback(message)


def _fallback(message: str):
    text = message.lower()
    requested_mode = _requested_schedule_mode(message)
    if requested_mode:
        return _execute_schedule_mode_change(requested_mode)
    requested_artifact = _requested_artifact_kind(message)
    if requested_artifact:
        return _execute_artifact_request(requested_artifact)

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
            hours = scheduler_current_schedule().get("hours_by_employee", {}).get(int(sarah["id"]), 0)
            return f"Sarah K. is a high-priority closer/cashier with a {sarah['max_hours']}h cap. She currently has {hours} scheduled hours and {sarah['callouts_this_month']} call-out cover this month."
    if "saturday" in text:
        sat = next(item for item in forecast if item["day"] == "Saturday")
        return f"Saturday forecast is ${sat['predicted_revenue']:.0f} with {sat['confidence_pct']}% confidence. Plan for about {sat['staff_needed']} staff across peak coverage."
    return (
        f"Weekly labor is currently {labor['weekly']['labor_pct']}% against a 30% target. "
        "Ask about busiest hours, overstaffing, Saturday forecast, Sarah, or labor reduction for a specific recommendation."
    )


def available_chat_agents():
    return [
        {"id": agent_id, "label": profile["label"], "description": profile["description"]}
        for agent_id, profile in AGENT_PROFILES.items()
    ]


def chat(message: str, history: list | None = None, agent: str | None = None):
    _load_local_env()
    requested_mode = _requested_schedule_mode(message)
    if requested_mode:
        return _execute_schedule_mode_change(requested_mode)
    requested_artifact = _requested_artifact_kind(message)
    if requested_artifact:
        return _execute_artifact_request(requested_artifact)

    if not _uses_vertex_ai() and not os.getenv("GOOGLE_API_KEY"):
        return _fallback(message)

    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return asyncio.run(_run_adk_chat(message, history, agent))
    except Exception:
        return _fallback(message)
