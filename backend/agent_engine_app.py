# =============================================================================
# Agent Engine Entrypoint
#
# This module provides a deployment-friendly ADK root agent for Google Agent
# Engine or other managed ADK runtimes. The FastAPI app is still the local/demo
# web backend, while this file gives the agent platform a clean object to load.
#
# Main responsibilities:
# - Load local environment settings when running outside Cloud Run/Agent Engine.
# - Export the Core Orchestrator as `root_agent`.
# - Keep the production agent entrypoint separate from HTTP API concerns.
#
# The root agent can still call the same ShiftIQ tools used by Manager Chat.
# Future Agent Engine deployment can point at this module and migrate tool
# access from direct function tools to `agents/mcp_registry.py` as needed.
# =============================================================================

from agents.assistant_agent import _load_local_env, build_adk_agent


_load_local_env()

root_agent = build_adk_agent("orchestrator")

