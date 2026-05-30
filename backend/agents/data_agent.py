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
    return pd.read_csv(path or data_path("availability.csv"))


def load_roles(path: str | Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or data_path("roles.csv"))
    df["required_roles"] = df["required_roles"].fillna("").apply(
        lambda value: [s.strip() for s in str(value).split("|") if s.strip()]
    )
    return df


def availability_summary(employee_id: int) -> str:
    availability = load_availability()
    row = availability[availability["employee_id"] == employee_id]
    if row.empty:
        return "Not submitted"
    days = [day[:3] for day in DAY_ORDER if int(row.iloc[0][day.lower()]) == 1]
    return ", ".join(days) if days else "Unavailable"


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
