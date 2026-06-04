# =============================================================================
# Scheduler Agent
#
# This file is the core scheduling engine for ShiftIQ. It converts forecasted
# demand, employee availability, employee skills, role requirements, wages, max
# hours, and priority into a weekly schedule. The MVP uses deterministic,
# explainable rules instead of OR-Tools or opaque optimization so the generated
# assignments can be shown and defended during a hackathon demo.
#
# Main responsibilities:
# - Generate weekly shift assignments for Opening, Midday, and Closing shifts.
# - Match required roles to employees who are available, certified, and under
#   their weekly hour caps.
# - Prioritize high-demand days first so Friday/Saturday coverage is protected.
# - Produce plain-English explanations for each assignment or unfilled role.
# - Track scheduled hours by employee for roster progress bars.
# - Calculate daily and weekly labor cost as a percentage of forecast revenue.
# - Replace assignments when the Call-Out Agent confirms a backup.
#
# Generated schedules are stored in shared in-memory state for the MVP. This
# keeps the demo simple while still letting the Schedule, Employees, Call-out,
# Labor Gauge, and Chat pages all reference the same current schedule.
# =============================================================================

from agents.data_agent import DAY_ORDER, availability_summary, load_availability, load_employees, load_roles
from agents.forecast_agent import forecast_next_week
from agents.staffing_agent import staffing_recommendation
from agents import state


def _employee_records():
    return load_employees().to_dict(orient="records")


def _hours_by_employee(schedule):
    hours = {}
    for shift in schedule:
        duration = shift["time_end"] - shift["time_start"]
        for assignment in shift["assigned"]:
            emp_id = assignment["employee_id"]
            hours[emp_id] = hours.get(emp_id, 0) + duration
    return hours


def generate_schedule(week_start: str = "2024-03-04"):
    employees = _employee_records()
    availability = load_availability()
    roles = load_roles()
    forecast = {item["day"]: item for item in forecast_next_week()}
    hours_assigned = {int(emp["id"]): 0 for emp in employees}
    schedule = []
    explanations = []

    scheduling_days = sorted(
        DAY_ORDER,
        key=lambda day: forecast.get(day, {}).get("predicted_revenue", 0),
        reverse=True,
    )

    for day in scheduling_days:
        day_col = day.lower()
        available_ids = availability[availability[day_col] == 1]["employee_id"].astype(int).tolist()
        daily_demand = forecast.get(day, {}).get("staff_needed", 2)

        for shift in roles.to_dict(orient="records"):
            duration = int(shift["time_end"] - shift["time_start"])
            assigned = []
            assigned_ids = set()
            unfilled = []
            staffing = staffing_recommendation(day, shift)
            base_roles = list(shift["required_roles"])
            threshold_staff = int(staffing["employees_needed"])
            target_staff = max(len(base_roles), threshold_staff)
            extra_slots = max(0, target_staff - len(base_roles))
            dynamic_roles = base_roles + ["Cashier"] * extra_slots

            explanations.append(
                {
                    "day": day,
                    "shift": shift["shift_name"],
                    "employee": None,
                    "role": "Staffing threshold",
                    "reason": (
                        f"{day} {shift['shift_name']} averages ${staffing['expected_hourly_revenue']:.0f}/hour, "
                        f"which falls in the {staffing['threshold']['label']} threshold. "
                        f"ShiftIQ targeted {target_staff} employees for this shift."
                    ),
                }
            )

            for required_role in dynamic_roles:
                candidates = []
                for emp in employees:
                    emp_id = int(emp["id"])
                    if emp_id not in available_ids or emp_id in assigned_ids:
                        continue
                    if required_role not in emp["skills"]:
                        continue
                    if hours_assigned[emp_id] + duration > int(emp["max_hours"]):
                        continue

                    remaining = int(emp["max_hours"]) - hours_assigned[emp_id]
                    score = 50
                    score += (4 - int(emp["priority"])) * 12
                    score += min(remaining, 20)
                    score += min(daily_demand, 6) * 2
                    score += min(threshold_staff, 6) * 2
                    score -= int(emp.get("callouts_this_month", 0)) * 3
                    candidates.append((score, remaining, emp))

                if not candidates:
                    unfilled.append(required_role)
                    explanations.append(
                        {
                            "day": day,
                            "shift": shift["shift_name"],
                            "employee": None,
                            "role": required_role,
                            "reason": f"No available certified employee could cover {required_role} for {day} {shift['shift_name']}.",
                        }
                    )
                    continue

                score, remaining, best = sorted(candidates, key=lambda item: item[0], reverse=True)[0]
                emp_id = int(best["id"])
                hours_assigned[emp_id] += duration
                assigned_ids.add(emp_id)
                assigned.append(
                    {
                        "employee_id": emp_id,
                        "name": best["name"],
                        "role": required_role,
                        "hourly_wage": float(best["hourly_wage"]),
                        "score": round(score, 1),
                    }
                )
                explanations.append(
                    {
                        "day": day,
                        "shift": shift["shift_name"],
                        "employee": best["name"],
                        "role": required_role,
                        "reason": (
                            f"Assigned {best['name']} to {required_role} on {day} {shift['shift_name']}: "
                            f"available {availability_summary(emp_id)}, certified, priority {best['priority']}, "
                            f"and {int(best['max_hours']) - hours_assigned[emp_id]}h remaining after assignment."
                        ),
                    }
                )

            schedule.append(
                {
                    "day": day,
                    "shift": shift["shift_name"],
                    "time_start": int(shift["time_start"]),
                    "time_end": int(shift["time_end"]),
                    "time": f"{int(shift['time_start'])}:00-{int(shift['time_end'])}:00",
                    "required_roles": dynamic_roles,
                    "base_required_roles": base_roles,
                    "target_staff": target_staff,
                    "staffing_threshold": staffing["threshold"],
                    "expected_hourly_revenue": staffing["expected_hourly_revenue"],
                    "extra_dynamic_slots": extra_slots,
                    "assigned": assigned,
                    "unfilled_roles": unfilled,
                }
            )

    shift_order = {row["shift_name"]: index for index, row in enumerate(roles.to_dict(orient="records"))}
    schedule.sort(key=lambda item: (DAY_ORDER.index(item["day"]), shift_order.get(item["shift"], 99)))
    result = {"week_start": week_start, "schedule": schedule, "explanations": explanations, "hours_by_employee": hours_assigned}
    state.current_schedule = result
    return result


def get_current_schedule():
    return state.current_schedule or {"week_start": None, "schedule": [], "explanations": [], "hours_by_employee": {}}


def edit_shift(day: str, shift_name: str, assignments: list[dict]):
    current = get_current_schedule()
    if not current["schedule"]:
        current = generate_schedule()

    employees = {int(emp["id"]): emp for emp in _employee_records()}
    target = next((shift for shift in current["schedule"] if shift["day"] == day and shift["shift"] == shift_name), None)
    if target is None:
        return current

    edited_assignments = []
    for assignment in assignments:
        employee_id = int(assignment["employee_id"])
        role = assignment["role"]
        employee = employees.get(employee_id)
        if employee is None:
            continue
        edited_assignments.append(
            {
                "employee_id": employee_id,
                "name": employee["name"],
                "role": role,
                "hourly_wage": float(employee["hourly_wage"]),
                "score": 100,
                "manual_override": True,
            }
        )

    target["assigned"] = edited_assignments
    target["unfilled_roles"] = []
    target["manual_override"] = True

    current["hours_by_employee"] = _hours_by_employee(current["schedule"])
    current.setdefault("explanations", []).append(
        {
            "day": day,
            "shift": shift_name,
            "employee": None,
            "role": "Manual edit",
            "reason": f"Manager manually edited {day} {shift_name}; labor and employee hours were recalculated.",
        }
    )
    state.current_schedule = current
    return current


def labor_summary():
    current = get_current_schedule()
    forecast = {item["day"]: item["predicted_revenue"] for item in forecast_next_week()}
    daily = {day: {"day": day, "labor_cost": 0.0, "revenue": forecast.get(day, 0), "labor_pct": 0.0, "status": "ok"} for day in DAY_ORDER}

    for shift in current["schedule"]:
        duration = shift["time_end"] - shift["time_start"]
        for assignment in shift["assigned"]:
            daily[shift["day"]]["labor_cost"] += float(assignment["hourly_wage"]) * duration

    for item in daily.values():
        item["labor_cost"] = round(item["labor_cost"], 2)
        item["labor_pct"] = round((item["labor_cost"] / max(item["revenue"], 1)) * 100, 1)
        item["status"] = "bad" if item["labor_pct"] > 35 else "warn" if item["labor_pct"] > 30 else "ok"

    total_labor = sum(item["labor_cost"] for item in daily.values())
    total_revenue = sum(item["revenue"] for item in daily.values())
    weekly_pct = round((total_labor / max(total_revenue, 1)) * 100, 1)
    return {
        "daily": list(daily.values()),
        "weekly": {
            "labor_cost": round(total_labor, 2),
            "revenue": round(total_revenue, 2),
            "labor_pct": weekly_pct,
            "status": "bad" if weekly_pct > 35 else "warn" if weekly_pct > 30 else "ok",
            "target_pct": 30,
        },
    }


def replace_assignment(day: str, shift_name: str, called_out_id: int, replacement_id: int):
    current = get_current_schedule()
    if not current["schedule"]:
        current = generate_schedule()
    employees = {int(emp["id"]): emp for emp in _employee_records()}
    replacement = employees[replacement_id]

    for shift in current["schedule"]:
        if shift["day"] == day and shift["shift"] == shift_name:
            for assignment in shift["assigned"]:
                if assignment["employee_id"] == called_out_id:
                    assignment["employee_id"] = replacement_id
                    assignment["name"] = replacement["name"]
                    assignment["hourly_wage"] = float(replacement["hourly_wage"])
                    assignment["score"] = 100
                    assignment["replacement"] = True
                    current["hours_by_employee"] = _hours_by_employee(current["schedule"])
                    state.current_schedule = current
                    return current
            for assignment in shift["assigned"]:
                if assignment["role"] in replacement["skills"]:
                    assignment["employee_id"] = replacement_id
                    assignment["name"] = replacement["name"]
                    assignment["hourly_wage"] = float(replacement["hourly_wage"])
                    assignment["score"] = 100
                    assignment["replacement"] = True
                    assignment["covered_for_employee_id"] = called_out_id
                    current["hours_by_employee"] = _hours_by_employee(current["schedule"])
                    state.current_schedule = current
                    return current
            if shift["assigned"]:
                shift["assigned"][0]["employee_id"] = replacement_id
                shift["assigned"][0]["name"] = replacement["name"]
                shift["assigned"][0]["hourly_wage"] = float(replacement["hourly_wage"])
                shift["assigned"][0]["score"] = 100
                shift["assigned"][0]["replacement"] = True
                shift["assigned"][0]["covered_for_employee_id"] = called_out_id
                current["hours_by_employee"] = _hours_by_employee(current["schedule"])
                state.current_schedule = current
                return current
    return current
