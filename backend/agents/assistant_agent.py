# =============================================================================
# Manager Assistant Agent
#
# This file powers the Manager Chat page. It turns the rest of the ShiftIQ data
# model into concise, manager-friendly answers about sales trends, labor cost,
# staffing risk, employee details, and schedule recommendations. The agent uses
# a hybrid strategy: if an OPENAI_API_KEY is configured, it can ask OpenAI to
# generate a response from live context; otherwise, it falls back to deterministic
# local responses so the hackathon demo always works without external services.
#
# Main responsibilities:
# - Build answers from live forecast, busiest-period, overstaffing, labor, and
#   employee data.
# - Provide reliable canned-but-data-grounded fallback answers for common demo
#   questions such as labor reduction, busiest hours, Sarah's status, and the
#   Saturday forecast.
# - Keep chat responses specific and practical by referencing real values from
#   the CSV-backed agents and the current in-memory schedule.
#
# This agent does not mutate schedules or data. It reads from other agents and
# explains what it finds in plain English.
# =============================================================================

import os

from agents.forecast_agent import forecast_next_week
from agents.insight_agent import get_busiest_periods, get_overstaffing_alerts
from agents.scheduler_agent import get_current_schedule, labor_summary
from agents.data_agent import load_employees


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
    if not os.getenv("OPENAI_API_KEY"):
        return _fallback(message)

    try:
        from openai import OpenAI

        context = {
            "forecast": forecast_next_week(),
            "busiest": get_busiest_periods(5),
            "alerts": get_overstaffing_alerts(),
            "labor": labor_summary(),
            "schedule": get_current_schedule(),
        }
        client = OpenAI()
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are ShiftIQ, a concise operations assistant. Answer with specific numbers from this context: "
                        f"{context}"
                    ),
                },
                *(history or []),
                {"role": "user", "content": message},
            ],
            max_tokens=350,
        )
        return response.choices[0].message.content
    except Exception:
        return _fallback(message)
