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

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


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
