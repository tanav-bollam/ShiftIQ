# =============================================================================
# Messaging And Call-Out Agent
#
# This file simulates employee communication for the ShiftIQ MVP. In a real
# product this layer could integrate with SMS, email, push notifications, or a
# workforce app. For the hackathon build, messages are written to in-memory
# state and displayed in the dashboard so the manager can see the flow without
# requiring Twilio or external credentials.
#
# Main responsibilities:
# - Generate weekly availability request messages for all employees.
# - Store simulated messages in the shared message log.
# - Evaluate backup candidates when an employee calls out.
# - Score candidates using availability, skill match, remaining hours, priority,
#   and recent call-out history.
# - Confirm a backup and update the current in-memory schedule through the
#   Scheduler Agent.
#
# This agent bridges scheduling decisions and manager-facing operations: it
# explains who should be contacted, why they are preferred, and records the
# simulated communication.
# =============================================================================

from agents import state
from agents.data_agent import is_available_for_window, load_availability, load_employees
from agents.persistence_agent import log_audit, save_runtime_state
from agents.scheduler_agent import get_current_schedule, replace_assignment


def request_availability(week_start: str):
    employees = load_employees()
    messages = []
    for emp in employees.to_dict(orient="records"):
        first = emp["name"].split()[0]
        msg = {
            "to": emp["name"],
            "channel": "in-app",
            "body": f"Hi {first}! Please submit availability for the week of {week_start} by Friday 5 PM.",
            "status": "sent",
        }
        messages.append(msg)
        state.message_log.append(msg)
    save_runtime_state("message_log", state.message_log)
    log_audit("message", "request_availability", "ok", {"week_start": week_start, "messages": len(messages)}, actor="manager")
    return messages


def find_backups(called_out_id: int, shift_name: str, day: str):
    employees = load_employees().to_dict(orient="records")
    availability = load_availability()
    current = get_current_schedule()
    called_out = next(emp for emp in employees if int(emp["id"]) == called_out_id)
    target_shift = next((s for s in current["schedule"] if s["day"] == day and s["shift"] == shift_name), None)
    needed_roles = []
    if target_shift:
        needed_roles = [
            assignment["role"]
            for assignment in target_shift["assigned"]
            if assignment["employee_id"] == called_out_id
        ] or target_shift["required_roles"]
    else:
        needed_roles = called_out["skills"]

    hours_used = current.get("hours_by_employee", {})
    candidates = []
    for emp in employees:
        emp_id = int(emp["id"])
        if emp_id == called_out_id:
            continue
        row = availability[availability["employee_id"] == emp_id]
        if row.empty:
            continue
        shift_start = target_shift["time_start"] if target_shift else 8
        shift_end = target_shift["time_end"] if target_shift else 22
        if not is_available_for_window(emp_id, day, shift_start, shift_end):
            continue
        role_match = any(role in emp["skills"] for role in needed_roles)
        hours_remaining = int(emp["max_hours"]) - int(hours_used.get(emp_id, 0))
        if hours_remaining <= 0:
            continue
        score = 25
        score += 45 if role_match else 0
        score += min(hours_remaining, 20)
        score += (4 - int(emp["priority"])) * 6
        score -= int(emp["callouts_this_month"]) * 4
        candidates.append(
            {
                "employee_id": emp_id,
                "name": emp["name"],
                "role": emp["role"],
                "skill_match": role_match,
                "needed_roles": needed_roles,
                "hours_remaining": hours_remaining,
                "callouts_this_month": int(emp["callouts_this_month"]),
                "score": max(0, round(score, 1)),
                "message": (
                    f"Hi {emp['name'].split()[0]}! {called_out['name']} called out for "
                    f"{shift_name} on {day}. Are you available to cover? Reply YES to confirm."
                ),
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    state.active_callout = {
        "employee_id": called_out_id,
        "employee_name": called_out["name"],
        "shift_name": shift_name,
        "day": day,
        "candidates": candidates,
    }
    log_audit("coverage", "find_backups", "ok", {"called_out_id": called_out_id, "day": day, "shift_name": shift_name, "candidate_count": len(candidates)}, actor="manager")
    return state.active_callout


def confirm_backup(called_out_id: int, replacement_id: int, shift_name: str, day: str):
    updated = replace_assignment(day, shift_name, called_out_id, replacement_id)
    employees = load_employees().set_index("id")
    replacement_name = employees.loc[replacement_id]["name"]
    called_out_name = employees.loc[called_out_id]["name"]
    msg = {
        "to": replacement_name,
        "channel": "in-app",
        "body": f"Confirmed: you are covering {shift_name} on {day} for {called_out_name}.",
        "status": "confirmed",
    }
    state.message_log.append(msg)
    save_runtime_state("message_log", state.message_log)
    state.active_callout = {**(state.active_callout or {}), "confirmed_backup": replacement_name}
    log_audit("coverage", "confirm_backup", "ok", {"called_out_id": called_out_id, "replacement_id": replacement_id, "day": day, "shift_name": shift_name}, actor="manager")
    return {"status": "confirmed", "schedule": updated, "message": msg}
