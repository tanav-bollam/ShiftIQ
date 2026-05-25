from agents import state
from agents.data_agent import load_availability, load_employees
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
        if row.empty or int(row.iloc[0][day.lower()]) != 1:
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
    state.active_callout = {**(state.active_callout or {}), "confirmed_backup": replacement_name}
    return {"status": "confirmed", "schedule": updated, "message": msg}
