# =============================================================================
# Shift Request Agent
#
# This file handles the employee-driven shift swap and open shift workflow for
# the ShiftIQ MVP. The scheduler generates the baseline weekly schedule, but
# real teams need a way for employees to give up shifts, request swaps, and pick
# up open coverage. This agent stores those requests in shared in-memory state
# and applies approved changes back into the current schedule.
#
# Main responsibilities:
# - Create employee shift requests from the employee portal.
# - List pending and resolved requests for both employee and manager views.
# - Track whether a request is a coverage request, swap request, or open shift
#   pickup.
# - Approve requests by either opening a role on a shift or replacing the
#   assigned employee with another qualified employee.
# - Recalculate scheduled hours after approvals so roster progress and labor
#   summaries stay in sync.
#
# This is intentionally lightweight and deterministic for the hackathon build.
# A production version would persist these requests, notify employees, and add
# approval permissions/audit logs.
# =============================================================================

from datetime import datetime, timedelta

from agents import state
from agents.data_agent import load_employees
from agents.persistence_agent import log_audit, save_runtime_state
from agents.scheduler_agent import generate_schedule, get_current_schedule, replace_assignment


AUTO_OPEN_NOTICE_HOURS = 48
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _employees_by_id():
    return {int(emp["id"]): emp for emp in load_employees().to_dict(orient="records")}


def _find_shift(day: str, shift_name: str):
    current = get_current_schedule()
    if not current["schedule"]:
        current = generate_schedule()
    return next((shift for shift in current["schedule"] if shift["day"] == day and shift["shift"] == shift_name), None)


def _employee_assignment(shift, employee_id: int):
    if not shift:
        return None
    return next((assignment for assignment in shift["assigned"] if int(assignment["employee_id"]) == employee_id), None)


def _shift_start_datetime(day: str, shift) -> datetime:
    now = datetime.now()
    target_day_index = DAY_ORDER.index(day)
    week_start = get_current_schedule().get("week_start")

    try:
        base = datetime.strptime(week_start, "%Y-%m-%d")
        candidate = base + timedelta(days=target_day_index)
        candidate = candidate.replace(hour=int(shift["time_start"]), minute=0, second=0, microsecond=0)
    except (TypeError, ValueError):
        days_ahead = (target_day_index - now.weekday()) % 7
        candidate = (now + timedelta(days=days_ahead)).replace(
            hour=int(shift["time_start"]),
            minute=0,
            second=0,
            microsecond=0,
        )

    if candidate <= now:
        days_ahead = (target_day_index - now.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        candidate = (now + timedelta(days=days_ahead)).replace(
            hour=int(shift["time_start"]),
            minute=0,
            second=0,
            microsecond=0,
        )
    return candidate


def _can_auto_open(request_type: str, day: str, shift) -> tuple[bool, float]:
    if request_type != "Offer shift" or not shift:
        return False, 0
    hours_until_shift = (_shift_start_datetime(day, shift) - datetime.now()).total_seconds() / 3600
    return hours_until_shift >= AUTO_OPEN_NOTICE_HOURS, round(hours_until_shift, 1)


def list_shift_requests(employee_id: int | None = None):
    requests = state.shift_requests
    if employee_id is not None:
        requests = [
            request
            for request in requests
            if int(request["employee_id"]) == employee_id or int(request.get("replacement_id") or 0) == employee_id
        ]
    return sorted(requests, key=lambda item: item["id"], reverse=True)


def create_shift_request(
    employee_id: int,
    request_type: str,
    day: str,
    shift_name: str,
    note: str = "",
    replacement_id: int | None = None,
):
    employees = _employees_by_id()
    employee = employees.get(employee_id)
    replacement = employees.get(replacement_id) if replacement_id else None
    shift = _find_shift(day, shift_name)
    assignment = _employee_assignment(shift, employee_id)
    role = assignment["role"] if assignment else (shift["required_roles"][0] if shift else "Cashier")
    auto_open, hours_until_shift = _can_auto_open(request_type, day, shift)

    request_id = state.next_shift_request_id
    state.next_shift_request_id += 1
    request = {
        "id": request_id,
        "employee_id": employee_id,
        "employee_name": employee["name"] if employee else f"Employee {employee_id}",
        "request_type": request_type,
        "day": day,
        "shift_name": shift_name,
        "time": shift["time"] if shift else "",
        "role": role,
        "replacement_id": replacement_id,
        "replacement_name": replacement["name"] if replacement else None,
        "note": note or "No note added",
        "status": "open" if auto_open else "pending",
        "manager_note": (
            f"Auto-opened because the shift is {hours_until_shift} hours away."
            if auto_open
            else "Manager approval required because this request is within 48 hours or is not a dropped shift."
        ),
        "auto_opened": auto_open,
        "hours_until_shift": hours_until_shift,
    }
    state.shift_requests.append(request)
    save_runtime_state("shift_requests", state.shift_requests)
    save_runtime_state("next_shift_request_id", state.next_shift_request_id)
    log_audit("shift_request", "create", request["status"], {"request": request}, actor=request["employee_name"])
    return request


def claim_open_shift(request_id: int, replacement_id: int, note: str = ""):
    employees = _employees_by_id()
    request = next((item for item in state.shift_requests if int(item["id"]) == request_id), None)
    if not request:
        return {"status": "error", "message": "Shift request not found"}
    replacement = employees.get(replacement_id)
    request["replacement_id"] = replacement_id
    request["replacement_name"] = replacement["name"] if replacement else f"Employee {replacement_id}"
    request["status"] = "claimed"
    request["claim_note"] = note or "Available to cover this shift."
    save_runtime_state("shift_requests", state.shift_requests)
    log_audit("shift_request", "claim", "claimed", {"request_id": request_id, "replacement_id": replacement_id}, actor=request["replacement_name"])
    return request


def approve_shift_request(request_id: int):
    request = next((item for item in state.shift_requests if int(item["id"]) == request_id), None)
    if not request:
        return {"status": "error", "message": "Shift request not found"}

    replacement_id = request.get("replacement_id")
    if not replacement_id:
        request["status"] = "open"
        request["manager_note"] = "Approved for coverage; waiting for another employee to claim it."
        save_runtime_state("shift_requests", state.shift_requests)
        log_audit("shift_request", "approve_open", "open", {"request_id": request_id}, actor="manager")
        return {"status": "open", "request": request, "schedule": get_current_schedule()}

    updated = replace_assignment(request["day"], request["shift_name"], int(request["employee_id"]), int(replacement_id))
    request["status"] = "approved"
    request["manager_note"] = f"Approved and assigned to {request['replacement_name']}."
    state.message_log.append(
        {
            "to": request["replacement_name"],
            "channel": "in-app",
            "body": f"Approved: you are now covering {request['day']} {request['shift_name']} for {request['employee_name']}.",
            "status": "approved",
        }
    )
    state.message_log.append(
        {
            "to": request["employee_name"],
            "channel": "in-app",
            "body": f"Approved: your {request['day']} {request['shift_name']} shift is covered by {request['replacement_name']}.",
            "status": "approved",
        }
    )
    save_runtime_state("shift_requests", state.shift_requests)
    save_runtime_state("message_log", state.message_log)
    log_audit("shift_request", "approve", "approved", {"request_id": request_id, "replacement_id": replacement_id}, actor="manager")
    return {"status": "approved", "request": request, "schedule": updated}
