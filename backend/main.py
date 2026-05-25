from pathlib import Path
import shutil
from typing import List

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import state
from agents.assistant_agent import chat
from agents.data_agent import DATA_DIR, availability_summary, load_employees
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
from agents.scheduler_agent import generate_schedule, get_current_schedule, labor_summary


app = FastAPI(title="ShiftIQ API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        emp["scheduled_hours"] = int(hours.get(emp_id, 0))
        records.append(emp)
    return records


@app.post("/upload/{file_type}")
async def upload_file(file_type: str, file: UploadFile = File(...)):
    allowed = {"sales", "employees", "availability", "roles"}
    if file_type not in allowed:
        return {"status": "error", "message": f"Unsupported file type: {file_type}"}
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"{file_type}.csv"
    with path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    state.current_schedule = None
    return {"status": "uploaded", "file": file_type}


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


@app.post("/schedule/generate")
def create_schedule(week_start: str = "2024-03-04"):
    return generate_schedule(week_start)


@app.get("/schedule/current")
def current_schedule():
    return get_current_schedule()


@app.get("/labor/summary")
def labor():
    return labor_summary()


@app.post("/messaging/request-availability")
def request_avail(week_start: str = "2024-03-04"):
    return request_availability(week_start)


@app.get("/messaging/log")
def messaging_log():
    return state.message_log


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
    return {"reply": chat(req.message, history)}
