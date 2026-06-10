# =============================================================================
# ShiftIQ MCP Server
#
# This module exposes ShiftIQ business capabilities through the Model Context
# Protocol (MCP). It is the bridge between the ADK agent team and external,
# standardized tool access. Instead of every agent knowing the internal Python
# module layout, an MCP host can discover and call these tools over the MCP
# protocol.
#
# Main responsibilities:
# - Publish schedule, labor, employee, coverage, and forecast tools through MCP.
# - Keep tool outputs JSON-safe so they can be consumed by ADK, inspectors, or
#   future external agent runtimes.
# - Provide a local stdio server for development and a streamable HTTP transport
#   for cloud/container deployment.
#
# Local development:
#   python mcp_server.py
#
# HTTP transport:
#   python mcp_server.py --transport http --host 0.0.0.0 --port 8010
# =============================================================================

from __future__ import annotations

import argparse
import asyncio
import json

from mcp.server.fastmcp import FastMCP

from agents.assistant_agent import (
    create_report_artifact,
    explain_schedule_assignment,
    get_employee_profile,
    get_labor_summary,
    get_sales_insights,
    get_schedule_summary,
    get_shiftiq_overview,
    optimize_labor_savings,
)
from agents.messaging_agent import find_backups
from agents.scheduler_agent import generate_schedule, get_current_schedule
from agents.weather_agent import weather_adjusted_forecast, weather_staffing_recommendations


def _json_safe(value):
    return json.loads(json.dumps(value, default=str))


mcp = FastMCP(
    "ShiftIQ MCP",
    instructions=(
        "Use these tools to inspect and operate ShiftIQ scheduling data. "
        "All outputs are derived from local CSV-backed data or the current "
        "in-memory ShiftIQ runtime state."
    ),
)


@mcp.tool()
def get_shift_iq_overview() -> dict:
    """Return a compact operating overview for ShiftIQ."""
    return _json_safe(get_shiftiq_overview())


@mcp.tool()
def get_labor_summary_tool() -> dict:
    """Return daily and weekly labor cost percentages."""
    return _json_safe(get_labor_summary())


@mcp.tool()
def get_current_schedule_tool() -> dict:
    """Return the current generated schedule."""
    return _json_safe(get_current_schedule())


@mcp.tool()
def get_sales_insights_tool() -> dict:
    """Return daily revenue, busiest periods, heatmap sample, top items, and overstaffing alerts."""
    return _json_safe(get_sales_insights())


@mcp.tool()
def get_employee_profile_tool(name_or_id: str) -> dict:
    """Look up an employee by name or id and include current scheduled hours."""
    return _json_safe(get_employee_profile(name_or_id))


@mcp.tool()
def explain_schedule_assignment_tool(name_or_id: str = "", day: str = "", shift_name: str = "") -> dict:
    """Explain schedule decisions for an employee, day, or shift."""
    return _json_safe(explain_schedule_assignment(name_or_id, day, shift_name))


@mcp.tool()
def generate_schedule_tool(mode: str = "block") -> dict:
    """Generate a block or flexible demand schedule."""
    normalized = "flexible" if str(mode).lower() == "flexible" else "block"
    return _json_safe(generate_schedule(mode=normalized))


@mcp.tool()
def find_backup_candidates_tool(called_out_id: int, day: str, shift_name: str) -> dict:
    """Rank employees who can cover a called-out employee's shift."""
    if not get_current_schedule().get("schedule"):
        generate_schedule()
    return _json_safe(find_backups(called_out_id, shift_name, day))


@mcp.tool()
def optimize_labor_savings_tool(target_savings: float = 200.0) -> dict:
    """Recommend labor-saving changes that approach a target savings amount."""
    return _json_safe(optimize_labor_savings(target_savings))


@mcp.tool()
def get_weather_aware_staffing_tool() -> dict:
    """Return weather-adjusted forecast and staffing recommendations."""
    return _json_safe(
        {
            "forecast": weather_adjusted_forecast(),
            "recommendations": weather_staffing_recommendations(),
        }
    )


@mcp.tool()
async def create_report_artifact_tool(kind: str = "weekly_schedule_csv") -> dict:
    """Create a schedule CSV, labor report, or staffing recommendations artifact."""
    return _json_safe(await create_report_artifact(kind))


def main():
    parser = argparse.ArgumentParser(description="Run the ShiftIQ MCP server.")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()

    if args.transport == "http":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        asyncio.run(mcp.run_streamable_http_async())
    else:
        mcp.run()


if __name__ == "__main__":
    main()
