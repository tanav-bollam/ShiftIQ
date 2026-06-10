# =============================================================================
# ShiftIQ API Entrypoint
#
# This file is the public HTTP layer for the ShiftIQ MVP. It creates the FastAPI
# application, configures local-demo CORS, defines request/response models, and
# exposes every endpoint consumed by the React dashboard. The business logic is
# intentionally kept out of this file and delegated to the agent modules in
# backend/agents so the API remains easy to scan and the product capabilities can
# evolve independently.
#
# Main responsibilities:
# - Serve health checks and CSV upload endpoints.
# - Expose POS insight, forecast, schedule, labor, messaging, call-out, and chat
#   routes to the frontend.
# - Convert incoming JSON bodies into typed Pydantic models for call-outs and
#   chat.
# - Coordinate agent calls and return JSON-safe objects to the React app.
#
# Runtime notes:
# - Generated schedules, call-outs, and messages live in in-memory state for the
#   hackathon MVP, so they reset when the backend restarts.
# - CSV files in the top-level data/ directory are the source of truth for
#   sample sales, employee, availability, and shift-role data.
# =============================================================================

from pathlib import Path
import shutil
from typing import List

from fastapi import FastAPI, File, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import state
from agents.assistant_agent import available_chat_agents, chat, list_report_artifacts, load_report_artifact
from agents.data_agent import DATA_DIR, availability_summary, availability_windows, load_editable_table, load_employees, load_roles, save_editable_table, update_employee_availability, validate_csv_upload
from agents.forecast_agent import forecast_next_week
from agents.insight_agent import (
    get_busiest_periods,
    get_daily_revenue,
    get_hourly_heatmap,
    get_overstaffing_alerts,
    get_summary,
    get_top_items,
)
from agents.messaging_agent import confirm_backup, find_backups, request_availability
from agents.notification_agent import get_notifications
from agents.persistence_agent import approve_request, list_approvals, list_audit, load_runtime_state, reject_request, save_runtime_state
from agents.policy_agent import policy_knowledge_overview, search_policy_knowledge
from agents.scheduler_agent import edit_shift, generate_schedule, get_current_schedule, labor_summary
from agents.staffing_agent import get_staffing_thresholds, update_staffing_thresholds
from agents.shift_request_agent import approve_shift_request, claim_open_shift, create_shift_request, list_shift_requests
from agents.weather_agent import get_weather_forecast, weather_adjusted_forecast, weather_staffing_recommendations


app = FastAPI(title="ShiftIQ API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def restore_persisted_state():
    state.current_schedule = load_runtime_state("current_schedule")
    state.message_log = load_runtime_state("message_log", [])
    state.shift_requests = load_runtime_state("shift_requests", [])
    state.next_shift_request_id = load_runtime_state("next_shift_request_id", 1)


class CalloutRequest(BaseModel):
    employee_id: int
    shift_name: str
    day: str


class ConfirmBackupRequest(BaseModel):
    called_out_id: int
    replacement_id: int
    shift_name: str
    day: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    agent: str = "orchestrator"


class ShiftAssignment(BaseModel):
    employee_id: int
    role: str


class EditShiftRequest(BaseModel):
    day: str
    shift_name: str
    assignments: List[ShiftAssignment]


class StaffingThreshold(BaseModel):
    min_revenue: float
    max_revenue: float | None = None
    employees_needed: int
    label: str = ""


class StaffingThresholdUpdate(BaseModel):
    thresholds: List[StaffingThreshold]


class DataTableUpdate(BaseModel):
    rows: List[dict]


class ShiftRequestCreate(BaseModel):
    employee_id: int
    request_type: str
    day: str
    shift_name: str
    note: str = ""
    replacement_id: int | None = None


class ShiftClaimRequest(BaseModel):
    replacement_id: int
    note: str = ""


class DayAvailability(BaseModel):
    available: bool = False
    start: str = "08:00"
    end: str = "22:00"


class AvailabilitySubmission(BaseModel):
    employee_id: int
    week_start: str = "2024-03-04"
    availability: dict[str, DayAvailability]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/employees")
def employees():
    current = get_current_schedule()
    hours = {int(k): v for k, v in current.get("hours_by_employee", {}).items()}
    records = []
    for emp in load_employees().to_dict(orient="records"):
        emp_id = int(emp["id"])
        emp["availability"] = availability_summary(emp_id)
        emp["availability_windows"] = availability_windows(emp_id)
        emp["scheduled_hours"] = int(hours.get(emp_id, 0))
        records.append(emp)
    return records


@app.get("/roles")
def roles():
    return load_roles().to_dict(orient="records")


@app.get("/staffing-thresholds")
def staffing_thresholds():
    return get_staffing_thresholds()


@app.put("/staffing-thresholds")
def save_staffing_thresholds(req: StaffingThresholdUpdate):
    thresholds = [item.model_dump() for item in req.thresholds]
    return update_staffing_thresholds(thresholds)


@app.get("/data-tables/{file_type}")
def data_table(file_type: str):
    return load_editable_table(file_type)


@app.put("/data-tables/{file_type}")
def save_data_table(file_type: str, req: DataTableUpdate):
    result = save_editable_table(file_type, req.rows)
    if result["status"] == "saved":
        state.current_schedule = None
        save_runtime_state("current_schedule", {"week_start": None, "mode": "block", "schedule": [], "explanations": [], "hours_by_employee": {}})
    return result


@app.post("/upload/{file_type}")
async def upload_file(file_type: str, file: UploadFile = File(...)):
    content = await file.read()
    validation = validate_csv_upload(file_type, content)
    if not validation["valid"]:
        return {"status": "error", "file": file_type, "validation": validation}
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"{file_type}.csv"
    with path.open("wb") as handle:
        handle.write(content)
    state.current_schedule = None
    save_runtime_state("current_schedule", {"week_start": None, "mode": "block", "schedule": [], "explanations": [], "hours_by_employee": {}})
    return {"status": "uploaded", "file": file_type, "validation": validation}


@app.post("/upload/{file_type}/preview")
async def preview_upload(file_type: str, file: UploadFile = File(...)):
    content = await file.read()
    return validate_csv_upload(file_type, content)


@app.get("/insights/summary")
def insights_summary():
    return get_summary(labor_summary())


@app.get("/insights/daily-revenue")
def daily_revenue():
    return get_daily_revenue()


@app.get("/insights/heatmap")
def heatmap():
    return get_hourly_heatmap()


@app.get("/insights/busiest")
def busiest():
    return get_busiest_periods()


@app.get("/insights/top-items")
def top_items():
    return get_top_items()


@app.get("/insights/overstaffing")
def overstaffing():
    return get_overstaffing_alerts()


@app.get("/forecast/next-week")
def next_week_forecast():
    return forecast_next_week()


@app.get("/forecast/weather-aware")
def weather_forecast():
    return {
        "weather": get_weather_forecast(),
        "forecast": weather_adjusted_forecast(),
        "recommendations": weather_staffing_recommendations(),
    }


@app.post("/schedule/generate")
def create_schedule(week_start: str = "2024-03-04", mode: str = "block"):
    return generate_schedule(week_start, mode)


@app.get("/schedule/current")
def current_schedule():
    return get_current_schedule()


@app.post("/schedule/edit-shift")
def edit_schedule_shift(req: EditShiftRequest):
    assignments = [{"employee_id": item.employee_id, "role": item.role} for item in req.assignments]
    return edit_shift(req.day, req.shift_name, assignments)


@app.get("/labor/summary")
def labor():
    return labor_summary()


@app.get("/employee/shift-requests")
def shift_requests(employee_id: int | None = None):
    return list_shift_requests(employee_id)


@app.post("/employee/shift-requests")
def create_employee_shift_request(req: ShiftRequestCreate):
    if not get_current_schedule()["schedule"]:
        generate_schedule()
    return create_shift_request(req.employee_id, req.request_type, req.day, req.shift_name, req.note, req.replacement_id)


@app.post("/employee/shift-requests/{request_id}/claim")
def claim_employee_shift_request(request_id: int, req: ShiftClaimRequest):
    return claim_open_shift(request_id, req.replacement_id, req.note)


@app.post("/employee/shift-requests/{request_id}/approve")
def approve_employee_shift_request(request_id: int):
    return approve_shift_request(request_id)


@app.post("/messaging/request-availability")
def request_avail(week_start: str = "2024-03-04"):
    return request_availability(week_start)


@app.post("/employee/availability")
def submit_employee_availability(req: AvailabilitySubmission):
    windows = {day: item.model_dump() for day, item in req.availability.items()}
    result = update_employee_availability(req.employee_id, req.week_start, windows)
    state.current_schedule = None
    save_runtime_state("current_schedule", {"week_start": None, "mode": "block", "schedule": [], "explanations": [], "hours_by_employee": {}})
    return result


@app.get("/messaging/log")
def messaging_log():
    return state.message_log


@app.get("/notifications")
def notifications(mode: str = "admin", employee_id: int | None = None):
    return get_notifications(mode, employee_id)


@app.get("/audit-log")
def audit_log(limit: int = 120):
    return list_audit(limit)


@app.get("/knowledge/overview")
def knowledge_overview():
    return policy_knowledge_overview()


@app.get("/knowledge/search")
def knowledge_search(q: str, limit: int = 4):
    return search_policy_knowledge(q, limit)


@app.get("/agent-approvals")
def agent_approvals(status: str | None = None):
    return list_approvals(status)


@app.post("/agent-approvals/{approval_id}/approve")
def approve_agent_action(approval_id: int):
    return approve_request(approval_id)


@app.post("/agent-approvals/{approval_id}/reject")
def reject_agent_action(approval_id: int):
    return reject_request(approval_id)


@app.post("/callouts/find-backups")
def callout_backups(req: CalloutRequest):
    if not get_current_schedule()["schedule"]:
        generate_schedule()
    return find_backups(req.employee_id, req.shift_name, req.day)


@app.post("/callouts/confirm-backup")
def callout_confirm(req: ConfirmBackupRequest):
    return confirm_backup(req.called_out_id, req.replacement_id, req.shift_name, req.day)


@app.post("/chat")
def manager_chat(req: ChatRequest):
    history = [{"role": item.role, "content": item.content} for item in req.history]
    return {"reply": chat(req.message, history, req.agent), "agent": req.agent}


@app.get("/chat/agents")
def chat_agents():
    return available_chat_agents()


@app.get("/chat/artifacts")
async def chat_artifacts():
    return await list_report_artifacts()


@app.get("/chat/artifacts/{filename}")
async def chat_artifact(filename: str):
    artifact = await load_report_artifact(filename)
    if artifact is None or artifact.inline_data is None:
        return Response(status_code=404)
    display_name = filename.replace("user:", "", 1)
    return Response(
        content=artifact.inline_data.data,
        media_type=artifact.inline_data.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{display_name}"'},
    )
