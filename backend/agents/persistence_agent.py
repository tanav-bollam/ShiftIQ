# =============================================================================
# Persistence And Audit Agent
#
# This file gives the ShiftIQ MVP a lightweight production-style persistence
# layer using SQLite. Earlier versions kept all generated schedules, messages,
# shift requests, agent approvals, and audit records only in process memory.
# That was fine for a static demo, but a hackathon production track benefits
# from durable state, action review, and an auditable record of agent behavior.
#
# Main responsibilities:
# - Initialize a local SQLite database in data/shiftiq.sqlite.
# - Persist runtime state snapshots such as the current generated schedule.
# - Store pending agent approvals before schedule-changing actions are applied.
# - Execute approved actions and record accepted/rejected decisions.
# - Record audit events for agent tools, scheduling actions, messages, and
#   manager approvals.
#
# The database remains intentionally small and self-contained. A production
# deployment can replace this module with Cloud SQL, Firestore, or AlloyDB while
# keeping the rest of the app's API behavior stable.
# =============================================================================

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "shiftiq.sqlite"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _json(value: Any):
    return json.dumps(value, default=str)


def init_db():
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runtime_state (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                actor TEXT NOT NULL,
                event_type TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                detail_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                decided_at TEXT,
                status TEXT NOT NULL,
                created_by TEXT NOT NULL,
                decided_by TEXT,
                action_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                impact TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                result_json TEXT
            );
            """
        )


def save_runtime_state(key: str, value: Any):
    init_db()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_state (key, value_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            (key, _json(value), _now()),
        )


def load_runtime_state(key: str, default=None):
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT value_json FROM runtime_state WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value_json"]) if row else default


def log_audit(event_type: str, action: str, status: str = "ok", detail: dict | None = None, actor: str = "system"):
    init_db()
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO audit_log (ts, actor, event_type, action, status, detail_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (_now(), actor, event_type, action, status, _json(detail or {})),
        )
        return cursor.lastrowid


def list_audit(limit: int = 120):
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "ts": row["ts"],
            "actor": row["actor"],
            "event_type": row["event_type"],
            "action": row["action"],
            "status": row["status"],
            "detail": json.loads(row["detail_json"]),
        }
        for row in rows
    ]


def create_approval(action_type: str, summary: str, impact: str, payload: dict, created_by: str = "agent"):
    init_db()
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO approvals (ts, status, created_by, action_type, summary, impact, payload_json)
            VALUES (?, 'pending', ?, ?, ?, ?, ?)
            """,
            (_now(), created_by, action_type, summary, impact, _json(payload)),
        )
        approval_id = cursor.lastrowid
    log_audit(
        "approval",
        "created",
        "pending",
        {"approval_id": approval_id, "action_type": action_type, "summary": summary, "impact": impact},
        actor=created_by,
    )
    return get_approval(approval_id)


def get_approval(approval_id: int):
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM approvals WHERE id = ?", (int(approval_id),)).fetchone()
    if not row:
        return None
    return _approval_row(row)


def list_approvals(status: str | None = None, limit: int = 100):
    init_db()
    query = "SELECT * FROM approvals"
    params: list[Any] = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(int(limit))
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_approval_row(row) for row in rows]


def _approval_row(row):
    return {
        "id": row["id"],
        "ts": row["ts"],
        "decided_at": row["decided_at"],
        "status": row["status"],
        "created_by": row["created_by"],
        "decided_by": row["decided_by"],
        "action_type": row["action_type"],
        "summary": row["summary"],
        "impact": row["impact"],
        "payload": json.loads(row["payload_json"]),
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
    }


def _execute_approval_action(approval: dict):
    action_type = approval["action_type"]
    payload = approval["payload"]
    if action_type == "schedule_mode":
        from agents.scheduler_agent import generate_schedule, labor_summary

        mode = payload.get("mode", "block")
        schedule = generate_schedule(mode=mode)
        return {
            "status": "applied",
            "mode": schedule.get("mode"),
            "schedule_count": len(schedule.get("schedule", [])),
            "labor": labor_summary(),
        }
    if action_type == "generate_schedule":
        from agents.scheduler_agent import generate_schedule, labor_summary

        schedule = generate_schedule(mode=payload.get("mode", "block"))
        return {
            "status": "applied",
            "mode": schedule.get("mode"),
            "schedule_count": len(schedule.get("schedule", [])),
            "labor": labor_summary(),
        }
    if action_type == "export":
        import asyncio
        from agents.assistant_agent import create_report_artifact

        artifact = asyncio.run(create_report_artifact(payload.get("kind", "weekly_schedule_csv")))
        return {"status": "created", "artifact": artifact}
    return {"status": "noop", "message": f"No executor registered for {action_type}."}


def approve_request(approval_id: int, decided_by: str = "manager"):
    approval = get_approval(approval_id)
    if not approval:
        return {"status": "error", "message": "Approval not found"}
    if approval["status"] != "pending":
        return {"status": "error", "message": "Approval already decided", "approval": approval}

    result = _execute_approval_action(approval)
    with _connect() as conn:
        conn.execute(
            """
            UPDATE approvals
            SET status = 'approved', decided_at = ?, decided_by = ?, result_json = ?
            WHERE id = ?
            """,
            (_now(), decided_by, _json(result), int(approval_id)),
        )
    log_audit("approval", "approved", "ok", {"approval_id": approval_id, "result": result}, actor=decided_by)
    return {"status": "approved", "approval": get_approval(approval_id), "result": result}


def reject_request(approval_id: int, decided_by: str = "manager"):
    approval = get_approval(approval_id)
    if not approval:
        return {"status": "error", "message": "Approval not found"}
    if approval["status"] != "pending":
        return {"status": "error", "message": "Approval already decided", "approval": approval}

    with _connect() as conn:
        conn.execute(
            """
            UPDATE approvals
            SET status = 'rejected', decided_at = ?, decided_by = ?, result_json = ?
            WHERE id = ?
            """,
            (_now(), decided_by, _json({"status": "rejected"}), int(approval_id)),
        )
    log_audit("approval", "rejected", "ok", {"approval_id": approval_id}, actor=decided_by)
    return {"status": "rejected", "approval": get_approval(approval_id)}


init_db()

