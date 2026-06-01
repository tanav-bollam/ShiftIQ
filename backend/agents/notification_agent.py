# =============================================================================
# Notification Agent
#
# This file builds the notification feed for ShiftIQ. Notifications are derived
# from live MVP state instead of stored as a separate database table: schedule
# state, shift requests, call-outs, labor guardrails, and simulated messages all
# become concise alerts for either the manager or a selected employee.
#
# Main responsibilities:
# - Return admin notifications for schedule, shift request, coverage, labor, and
#   message events.
# - Return employee notifications for personal schedule, open shifts, request
#   updates, coverage messages, and availability reminders.
# - Keep the feed grouped into the MVP categories used by the UI: Schedule,
#   Shift Requests, Coverage, and Messages.
# - Avoid requiring real push infrastructure while still showing realistic
#   notification content in the dashboard.
#
# Notifications are not persisted independently. If the backend restarts, the
# feed is rebuilt from whatever in-memory schedule/messages/requests currently
# exist plus static CSV employee data.
# =============================================================================

from agents import state
from agents.data_agent import DAY_ORDER, load_availability, load_employees
from agents.scheduler_agent import get_current_schedule, labor_summary


def _notification(notification_id: str, category: str, title: str, body: str, priority: str = "normal", action_url: str = ""):
    return {
        "id": notification_id,
        "category": category,
        "title": title,
        "body": body,
        "priority": priority,
        "action_url": action_url,
        "unread": True,
    }


def _employee_name(employee_id: int) -> str:
    employees = load_employees()
    row = employees[employees["id"] == employee_id]
    return row.iloc[0]["name"] if not row.empty else f"Employee {employee_id}"


def _employee_record(employee_id: int):
    employees = load_employees()
    row = employees[employees["id"] == employee_id]
    return row.iloc[0].to_dict() if not row.empty else None


def _employee_can_cover(employee_id: int, request: dict) -> bool:
    employee = _employee_record(employee_id)
    if not employee:
        return False
    if request.get("role") not in employee.get("skills", []):
        return False
    availability = load_availability()
    row = availability[availability["employee_id"] == employee_id]
    if row.empty:
        return False
    return int(row.iloc[0][request["day"].lower()]) == 1


def admin_notifications():
    notifications = []
    current = get_current_schedule()
    schedule = current.get("schedule", [])
    labor = labor_summary().get("weekly", {})

    if schedule:
        open_roles = sum(len(shift.get("unfilled_roles", [])) for shift in schedule)
        notifications.append(
            _notification(
                "admin-schedule-published",
                "Schedule",
                "Schedule is active",
                f"{len(schedule)} shift blocks are loaded for this week.",
                "normal",
                "/schedule",
            )
        )
        if open_roles:
            notifications.append(
                _notification(
                    "admin-unfilled-roles",
                    "Schedule",
                    "Unfilled roles need attention",
                    f"{open_roles} role slots are still open on the weekly schedule.",
                    "high",
                    "/schedule",
                )
            )

    if labor.get("status") in {"warn", "bad"}:
        notifications.append(
            _notification(
                "admin-labor-guardrail",
                "Schedule",
                "Labor is above target",
                f"Weekly labor is {labor.get('labor_pct')}% against a 30% target.",
                "high" if labor.get("status") == "bad" else "normal",
                "/insights",
            )
        )

    for request in state.shift_requests:
        if request["status"] in {"pending", "claimed"}:
            dropped = request["request_type"] == "Offer shift"
            notifications.append(
                _notification(
                    f"admin-shift-request-{request['id']}",
                    "Shift Requests",
                    f"{request['employee_name']} dropped a shift" if dropped else f"{request['employee_name']} needs approval",
                    (
                        f"Priority coverage needed for {request['day']} {request['shift_name']} "
                        f"({request['role']})."
                        if dropped
                        else f"{request['request_type']} for {request['day']} {request['shift_name']} is {request['status']}."
                    ),
                    "high" if dropped or request["status"] == "claimed" else "normal",
                    "/schedule",
                )
            )
        if request["status"] == "open":
            notifications.append(
                _notification(
                    f"admin-open-shift-{request['id']}",
                    "Coverage",
                    "Priority open shift waiting for pickup" if request["request_type"] == "Offer shift" else "Open shift waiting for pickup",
                    f"{request['day']} {request['shift_name']} is open for {request['role']}.",
                    "high" if request["request_type"] == "Offer shift" else "normal",
                    "/schedule",
                )
            )

    if state.active_callout:
        callout = state.active_callout
        notifications.append(
            _notification(
                "admin-active-callout",
                "Coverage",
                "Call-out scenario active",
                f"{callout.get('employee_name')} called out for {callout.get('day')} {callout.get('shift_name')}.",
                "high",
                "/callout",
            )
        )

    recent_messages = state.message_log[-3:]
    for index, message in enumerate(reversed(recent_messages)):
        notifications.append(
            _notification(
                f"admin-message-{index}",
                "Messages",
                f"Message to {message.get('to')}",
                message.get("body", "Message sent."),
                "normal",
                "/employees",
            )
        )

    if not notifications:
        notifications.append(
            _notification(
                "admin-clear",
                "Messages",
                "No urgent notifications",
                "Schedule, coverage, and labor are quiet right now.",
                "normal",
                "/",
            )
        )

    return notifications


def employee_notifications(employee_id: int):
    notifications = []
    employee_name = _employee_name(employee_id)
    current = get_current_schedule()
    schedule = current.get("schedule", [])
    employee_shifts = [
        shift
        for shift in schedule
        if any(int(assignment["employee_id"]) == employee_id for assignment in shift.get("assigned", []))
    ]

    if employee_shifts:
        next_shift = sorted(employee_shifts, key=lambda item: (DAY_ORDER.index(item["day"]), item["time_start"]))[0]
        notifications.append(
            _notification(
                f"employee-next-shift-{employee_id}",
                "Schedule",
                "Upcoming shift",
                f"Your next shift is {next_shift['day']} {next_shift['shift']} from {next_shift['time']}.",
                "normal",
                "/employee/schedule",
            )
        )
    else:
        notifications.append(
            _notification(
                f"employee-no-shifts-{employee_id}",
                "Schedule",
                "No shifts assigned yet",
                "Check back after the manager publishes the schedule.",
                "normal",
                "/employee/schedule",
            )
        )

    for request in state.shift_requests:
        if int(request["employee_id"]) == employee_id or int(request.get("replacement_id") or 0) == employee_id:
            notifications.append(
                _notification(
                    f"employee-request-{request['id']}",
                    "Shift Requests",
                    f"Request {request['status']}",
                    f"{request['request_type']} for {request['day']} {request['shift_name']} is {request['status']}.",
                    "high" if request["status"] in {"claimed", "approved"} else "normal",
                    "/employee/requests",
                )
            )
        elif request["status"] == "open" and _employee_can_cover(employee_id, request):
            dropped = request["request_type"] == "Offer shift"
            notifications.append(
                _notification(
                    f"employee-open-shift-{request['id']}",
                    "Coverage",
                    "Priority shift available" if dropped else "Open shift available",
                    f"{request['day']} {request['shift_name']} needs {request['role']} coverage.",
                    "high" if dropped else "normal",
                    "/employee/requests",
                )
            )

    direct_messages = [message for message in state.message_log if message.get("to") == employee_name]
    for index, message in enumerate(reversed(direct_messages[-8:])):
        body = message.get("body", "")
        notifications.append(
            _notification(
                f"employee-message-{index}",
                "Messages",
                message.get("status", "Message").title(),
                body,
                "high" if "cover" in body.lower() else "normal",
                "/employee/messages",
            )
        )

    notifications.append(
        _notification(
            f"employee-availability-{employee_id}",
            "Messages",
            "Availability reminder",
            "Submit next week's availability before Friday at 5 PM.",
            "normal",
            "/employee/availability",
        )
    )

    return notifications


def get_notifications(mode: str, employee_id: int | None = None):
    notifications = employee_notifications(employee_id or 1) if mode == "employee" else admin_notifications()
    counts = {
        "all": len(notifications),
        "Schedule": 0,
        "Shift Requests": 0,
        "Coverage": 0,
        "Messages": 0,
    }
    for item in notifications:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    return {"mode": mode, "employee_id": employee_id, "counts": counts, "notifications": notifications[:12]}
