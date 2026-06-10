# =============================================================================
# ADK MCP Registry
#
# This file centralizes how ShiftIQ's ADK agents can connect to the local
# ShiftIQ MCP server. The current production chat path uses direct function
# tools for speed and reliability, while this registry provides the standard
# MCP Toolset configuration needed for Agent Engine or future hosted agent
# runtimes.
#
# Main responsibilities:
# - Construct an ADK McpToolset backed by backend/mcp_server.py over stdio.
# - Keep MCP tool selection explicit, making it easier to explain and audit
#   which externalized tools the agent can call.
# - Provide a single import point for future migration from direct function
#   tools to MCP-hosted tools.
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

from google.adk.tools.mcp_tool import McpToolset
from mcp import StdioServerParameters


MCP_SERVER_PATH = Path(__file__).resolve().parents[1] / "mcp_server.py"


SHIFTIQ_MCP_TOOLS = [
    "get_shift_iq_overview",
    "get_labor_summary_tool",
    "get_current_schedule_tool",
    "get_sales_insights_tool",
    "get_employee_profile_tool",
    "explain_schedule_assignment_tool",
    "generate_schedule_tool",
    "find_backup_candidates_tool",
    "optimize_labor_savings_tool",
    "create_report_artifact_tool",
]


def build_shiftiq_mcp_toolset(tool_filter: list[str] | None = None) -> McpToolset:
    """Create an ADK MCP toolset for the local ShiftIQ MCP server."""
    return McpToolset(
        connection_params=StdioServerParameters(
            command=sys.executable,
            args=[str(MCP_SERVER_PATH)],
        ),
        tool_filter=tool_filter or SHIFTIQ_MCP_TOOLS,
        tool_name_prefix="shiftiq_",
    )

