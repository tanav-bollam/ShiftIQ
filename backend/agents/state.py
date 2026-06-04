# =============================================================================
# Shared Runtime State
#
# This file holds the small amount of mutable in-memory state used by the
# ShiftIQ hackathon MVP. The static business inputs live in CSV files, but the
# generated schedule, active call-out, and simulated message log are runtime
# artifacts created as the manager interacts with the dashboard.
#
# Main responsibilities:
# - Store the latest generated schedule so multiple endpoints and pages can read
#   the same assignments.
# - Store the active call-out scenario and candidate list during the call-out
#   workflow.
# - Store simulated availability and backup messages for the Employees and
#   Call-out pages.
#
# This is deliberately not persistent. Restarting the backend clears these
# values, which is acceptable for the MVP. A production version would replace
# this file with database tables or another persistence layer.
# =============================================================================

current_schedule = None
active_callout = None
message_log = []
shift_requests = []
next_shift_request_id = 1
staffing_thresholds = [
    {"min_revenue": 0, "max_revenue": 300, "employees_needed": 2, "label": "Slow"},
    {"min_revenue": 301, "max_revenue": 600, "employees_needed": 3, "label": "Steady"},
    {"min_revenue": 601, "max_revenue": 900, "employees_needed": 4, "label": "Busy"},
    {"min_revenue": 901, "max_revenue": None, "employees_needed": 5, "label": "Peak"},
]
