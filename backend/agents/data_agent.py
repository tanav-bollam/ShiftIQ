# =============================================================================
# Data Agent
#
# This file is the data access foundation for the ShiftIQ MVP. Every other agent
# depends on it to load and normalize the sample CSV files from the top-level
# data/ directory. It replaces a real POS or workforce database for the
# hackathon version while keeping the rest of the app written as if data were
# coming from a structured backend.
#
# Main responsibilities:
# - Locate the project data directory reliably from the backend package.
# - Load sales, employees, availability, and role requirements from CSV files.
# - Normalize types used by downstream agents, such as dates, numeric hours,
#   revenue, transaction counts, and pipe-delimited skill lists.
# - Provide shared constants such as DAY_ORDER so charts, forecasts, and
#   schedules always present days consistently.
# - Convert an employee's weekly availability row into a compact display string
#   for the Employees page and scheduling explanations.
#
# If ShiftIQ later connects to a real POS system or database, this is the module
# most likely to become the adapter layer while the insight, forecast, and
# scheduling agents can keep their current interfaces.
# =============================================================================

from pathlib import Path
from io import BytesIO

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
REQUIRED_COLUMNS = {
    "sales": ["date", "day_of_week", "hour", "item_name", "revenue", "transaction_count"],
    "employees": ["id", "name", "role", "skills", "hourly_wage", "max_hours", "priority", "phone", "status", "callouts_this_month"],
    "availability": ["employee_id", "week_start", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
    "roles": ["shift_name", "time_start", "time_end", "required_roles"],
}
AVAILABILITY_TIME_COLUMNS = [
    f"{day}_{suffix}"
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for suffix in ["start", "end"]
]


def data_path(filename: str) -> Path:
    return DATA_DIR / filename


def load_sales(path: str | Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or data_path("sales.csv"), parse_dates=["date"])
    df["day_of_week"] = df["date"].dt.day_name()
    df["hour"] = df["hour"].astype(int)
    df["revenue"] = df["revenue"].astype(float)
    df["transaction_count"] = df["transaction_count"].astype(int)
    return df


def load_employees(path: str | Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or data_path("employees.csv"))
    df["skills"] = df["skills"].fillna("").apply(lambda value: [s.strip() for s in str(value).split("|") if s.strip()])
    return df


def load_availability(path: str | Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or data_path("availability.csv"))
    for column in AVAILABILITY_TIME_COLUMNS:
        if column not in df.columns:
            df[column] = ""
    return df


def _format_time(value) -> str:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return ""
    text = str(value).strip()
    if ":" in text:
        hour, minute = text.split(":", 1)
        return f"{int(float(hour)):02d}:{int(float(minute[:2] or 0)):02d}"
    return f"{int(float(text)):02d}:00"


def _time_to_hour(value, fallback: int) -> float:
    formatted = _format_time(value)
    if not formatted:
        return float(fallback)
    hour, minute = formatted.split(":", 1)
    return int(hour) + int(minute) / 60


def availability_windows(employee_id: int) -> dict:
    availability = load_availability()
    row = availability[availability["employee_id"] == employee_id]
    if row.empty:
        return {}
    item = row.iloc[0]
    windows = {}
    for day in [name.lower() for name in DAY_ORDER]:
        is_available = int(item.get(day, 0) or 0) == 1
        start = _format_time(item.get(f"{day}_start", "")) or "08:00"
        end = _format_time(item.get(f"{day}_end", "")) or "22:00"
        windows[day] = {"available": is_available, "start": start, "end": end}
    return windows


def is_available_for_window(employee_id: int, day: str, time_start: int | float, time_end: int | float) -> bool:
    windows = availability_windows(employee_id)
    window = windows.get(day.lower())
    if not window or not window["available"]:
        return False
    available_start = _time_to_hour(window["start"], 8)
    available_end = _time_to_hour(window["end"], 22)
    return available_start <= float(time_start) and available_end >= float(time_end)


def available_employee_ids_for_window(availability: pd.DataFrame, day: str, time_start: int | float, time_end: int | float) -> list[int]:
    day_col = day.lower()
    available_rows = availability[availability[day_col] == 1]
    return [
        int(row["employee_id"])
        for row in available_rows.to_dict(orient="records")
        if is_available_for_window(int(row["employee_id"]), day, time_start, time_end)
    ]


def load_roles(path: str | Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or data_path("roles.csv"))
    df["required_roles"] = df["required_roles"].fillna("").apply(
        lambda value: [s.strip() for s in str(value).split("|") if s.strip()]
    )
    return df


def availability_summary(employee_id: int) -> str:
    windows = availability_windows(employee_id)
    if not windows:
        return "Not submitted"
    days = []
    for day in DAY_ORDER:
        window = windows.get(day.lower())
        if not window or not window["available"]:
            continue
        if window["start"] == "08:00" and window["end"] == "22:00":
            days.append(day[:3])
        else:
            days.append(f"{day[:3]} {window['start']}-{window['end']}")
    return ", ".join(days) if days else "Unavailable"


def update_employee_availability(employee_id: int, week_start: str, windows: dict) -> dict:
    path = data_path("availability.csv")
    df = load_availability(path)
    employee_id = int(employee_id)
    mask = df["employee_id"].astype(int) == employee_id
    if not mask.any():
        row = {"employee_id": employee_id, "week_start": week_start}
        for day in [name.lower() for name in DAY_ORDER]:
            row[day] = 0
            row[f"{day}_start"] = ""
            row[f"{day}_end"] = ""
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        mask = df["employee_id"].astype(int) == employee_id

    df.loc[mask, "week_start"] = week_start
    for day in [name.lower() for name in DAY_ORDER]:
        window = windows.get(day, {})
        available = 1 if window.get("available") else 0
        start = _format_time(window.get("start", "")) if available else ""
        end = _format_time(window.get("end", "")) if available else ""
        if available and (not start or not end):
            start, end = "08:00", "22:00"
        df.loc[mask, day] = available
        df.loc[mask, f"{day}_start"] = start
        df.loc[mask, f"{day}_end"] = end

    base_columns = REQUIRED_COLUMNS["availability"]
    extra_columns = [column for column in AVAILABILITY_TIME_COLUMNS if column in df.columns]
    df = df[base_columns + extra_columns]
    df.to_csv(path, index=False)
    return {"status": "saved", "employee_id": employee_id, "week_start": week_start, "availability": availability_windows(employee_id)}


def validate_csv_upload(file_type: str, content: bytes) -> dict:
    required = REQUIRED_COLUMNS.get(file_type)
    if not required:
        return {"valid": False, "file_type": file_type, "errors": [f"Unsupported file type: {file_type}"], "warnings": [], "preview": []}

    errors = []
    warnings = []
    try:
        df = pd.read_csv(BytesIO(content))
    except Exception as exc:
        return {"valid": False, "file_type": file_type, "errors": [f"Could not parse CSV: {exc}"], "warnings": [], "preview": []}

    missing = [column for column in required if column not in df.columns]
    extra = [column for column in df.columns if column not in required]
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")
    if extra:
        warnings.append(f"Extra columns will be kept but are not used by the MVP: {', '.join(extra)}")
    if df.empty:
        errors.append("CSV has no data rows.")

    if file_type == "sales" and not errors:
        hours = pd.to_numeric(df["hour"], errors="coerce")
        revenue = pd.to_numeric(df["revenue"], errors="coerce")
        transactions = pd.to_numeric(df["transaction_count"], errors="coerce")
        invalid_hours = df[~hours.between(0, 23)]
        if not invalid_hours.empty:
            errors.append("Sales hours must be between 0 and 23.")
        if revenue.isna().any() or transactions.isna().any():
            errors.append("Revenue and transaction_count must be populated.")
    if file_type == "availability" and not errors:
        for day in [item.lower() for item in DAY_ORDER]:
            invalid = ~df[day].isin([0, 1])
            if invalid.any():
                errors.append(f"{day} availability values must be 0 or 1.")
                break
        for day in [item.lower() for item in DAY_ORDER]:
            start_col = f"{day}_start"
            end_col = f"{day}_end"
            if start_col in df.columns and end_col in df.columns:
                starts = df[start_col].fillna("").apply(lambda value: _time_to_hour(value, 8) if str(value).strip() else None)
                ends = df[end_col].fillna("").apply(lambda value: _time_to_hour(value, 22) if str(value).strip() else None)
                invalid_windows = [
                    index
                    for index, start in starts.items()
                    if start is not None and ends[index] is not None and ends[index] <= start
                ]
                if invalid_windows:
                    errors.append(f"{day} availability end times must be after start times.")
                    break
    if file_type == "roles" and not errors:
        starts = pd.to_numeric(df["time_start"], errors="coerce")
        ends = pd.to_numeric(df["time_end"], errors="coerce")
        if starts.isna().any() or ends.isna().any() or (ends <= starts).any():
            errors.append("Each role row must have time_end greater than time_start.")
    if file_type == "employees" and not errors:
        max_hours = pd.to_numeric(df["max_hours"], errors="coerce")
        wages = pd.to_numeric(df["hourly_wage"], errors="coerce")
        if max_hours.isna().any() or (max_hours <= 0).any():
            errors.append("Employee max_hours must be greater than 0.")
        if wages.isna().any() or (wages <= 0).any():
            errors.append("Employee hourly_wage must be greater than 0.")

    preview = df.head(5).fillna("").to_dict(orient="records")
    return {
        "valid": not errors,
        "file_type": file_type,
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "required_columns": required,
        "errors": errors,
        "warnings": warnings,
        "preview": preview,
    }


def load_editable_table(file_type: str) -> dict:
    required = REQUIRED_COLUMNS.get(file_type)
    if not required:
        return {"status": "error", "errors": [f"Unsupported file type: {file_type}"]}

    df = pd.read_csv(data_path(f"{file_type}.csv"), dtype=str, keep_default_na=False).fillna("")
    return {
        "status": "ok",
        "file_type": file_type,
        "columns": list(df.columns),
        "required_columns": required,
        "row_count": int(len(df)),
        "rows": df.to_dict(orient="records"),
    }


def save_editable_table(file_type: str, rows: list[dict]) -> dict:
    required = REQUIRED_COLUMNS.get(file_type)
    if not required:
        return {"status": "error", "errors": [f"Unsupported file type: {file_type}"]}
    if not rows:
        return {"status": "error", "errors": ["At least one row is required."]}

    df = pd.DataFrame(rows).fillna("")
    for column in required:
        if column not in df.columns:
            df[column] = ""
    columns = list(df.columns)
    ordered = required + [column for column in columns if column not in required]
    df = df[ordered]

    if file_type == "sales":
        parsed_dates = pd.to_datetime(df["date"], errors="coerce")
        valid_dates = ~parsed_dates.isna()
        df.loc[valid_dates, "date"] = parsed_dates[valid_dates].dt.strftime("%Y-%m-%d")
        df.loc[valid_dates, "day_of_week"] = parsed_dates[valid_dates].dt.day_name()

    path = data_path(f"{file_type}.csv")
    had_bom = path.exists() and path.read_bytes().startswith(b"\xef\xbb\xbf")
    content = df.to_csv(index=False).encode("utf-8-sig" if had_bom else "utf-8")
    validation = validate_csv_upload(file_type, content)
    if not validation["valid"]:
        return {"status": "error", "validation": validation, "errors": validation["errors"]}

    DATA_DIR.mkdir(exist_ok=True)
    with path.open("wb") as handle:
        handle.write(content)
    return {"status": "saved", "file_type": file_type, "validation": validation}
