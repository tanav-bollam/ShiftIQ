# =============================================================================
# Staffing Agent
#
# This file owns ShiftIQ's dynamic staffing threshold rules. The scheduler uses
# these rules to convert expected sales volume into the number of people a shift
# should carry. That lets the MVP move beyond fixed role templates: a slow shift
# can stay lean, while a high-revenue rush period receives additional employee
# slots automatically.
#
# Main responsibilities:
# - Store and validate editable revenue-to-staff thresholds in shared MVP state.
# - Calculate expected average hourly revenue for each day/shift from POS sales.
# - Match a shift's expected hourly revenue to the correct threshold band.
# - Return explainable staffing recommendations for the schedule generator and
#   frontend settings screens.
#
# The thresholds are intentionally in memory for the hackathon MVP. A production
# version would persist them as store-level scheduling settings.
# =============================================================================

from agents import state
from agents.data_agent import load_sales


def get_staffing_thresholds():
    return [dict(rule) for rule in state.staffing_thresholds]


def validate_staffing_thresholds(thresholds: list[dict]):
    errors = []
    cleaned = []

    if not thresholds:
        return [], ["At least one staffing threshold is required."]

    for index, item in enumerate(thresholds):
        try:
            min_revenue = float(item.get("min_revenue", 0))
            raw_max = item.get("max_revenue")
            max_revenue = None if raw_max in (None, "", "None") else float(raw_max)
            employees_needed = int(item.get("employees_needed", 0))
        except (TypeError, ValueError):
            errors.append(f"Threshold {index + 1} has invalid numbers.")
            continue

        label = str(item.get("label") or f"Band {index + 1}").strip()
        if min_revenue < 0:
            errors.append(f"Threshold {index + 1} minimum revenue cannot be negative.")
        if max_revenue is not None and max_revenue < min_revenue:
            errors.append(f"Threshold {index + 1} max revenue must be greater than min revenue.")
        if employees_needed < 1:
            errors.append(f"Threshold {index + 1} must require at least one employee.")

        cleaned.append(
            {
                "min_revenue": round(min_revenue, 2),
                "max_revenue": round(max_revenue, 2) if max_revenue is not None else None,
                "employees_needed": employees_needed,
                "label": label,
            }
        )

    cleaned.sort(key=lambda rule: rule["min_revenue"])
    for prev, current in zip(cleaned, cleaned[1:]):
        if prev["max_revenue"] is None:
            errors.append("Only the last threshold can be open-ended.")
        elif current["min_revenue"] <= prev["max_revenue"]:
            errors.append("Staffing thresholds cannot overlap.")

    open_ended = [rule for rule in cleaned if rule["max_revenue"] is None]
    if len(open_ended) > 1:
        errors.append("Only one staffing threshold can be open-ended.")

    return cleaned, errors


def update_staffing_thresholds(thresholds: list[dict]):
    cleaned, errors = validate_staffing_thresholds(thresholds)
    if errors:
        return {"status": "error", "errors": errors, "thresholds": get_staffing_thresholds()}

    state.staffing_thresholds = cleaned
    state.current_schedule = None
    return {"status": "updated", "thresholds": get_staffing_thresholds()}


def match_staffing_threshold(hourly_revenue: float):
    thresholds = get_staffing_thresholds()
    for rule in thresholds:
        max_revenue = rule["max_revenue"]
        if hourly_revenue >= rule["min_revenue"] and (max_revenue is None or hourly_revenue <= max_revenue):
            return dict(rule)
    return dict(thresholds[-1])


def expected_shift_hourly_revenue(day: str, time_start: int, time_end: int):
    sales = load_sales()
    hourly_totals = sales.groupby(["date", "day_of_week", "hour"], as_index=False)["revenue"].sum()
    window = hourly_totals[
        (hourly_totals["day_of_week"] == day)
        & (hourly_totals["hour"] >= int(time_start))
        & (hourly_totals["hour"] < int(time_end))
    ]
    if window.empty:
        return 0.0
    return round(float(window["revenue"].mean()), 2)


def staffing_recommendation(day: str, shift: dict):
    hourly_revenue = expected_shift_hourly_revenue(day, shift["time_start"], shift["time_end"])
    threshold = match_staffing_threshold(hourly_revenue)
    return {
        "day": day,
        "shift": shift["shift_name"],
        "expected_hourly_revenue": hourly_revenue,
        "threshold": threshold,
        "employees_needed": int(threshold["employees_needed"]),
    }
