# =============================================================================
# Agent Engine Deployment Helper
#
# This script is the deployment bridge between ShiftIQ's ADK root agent and
# Google Agent Runtime / Agent Engine. The Cloud Run app hosts the dashboard and
# HTTP API; this script packages the ADK `root_agent` from agent_engine_app.py
# so the agent itself can be deployed to Google's managed agent runtime.
#
# Usage:
#   cd backend
#   python deploy_agent_engine.py
#
# Required environment:
#   GOOGLE_CLOUD_PROJECT=your-project-id
#   GOOGLE_CLOUD_LOCATION=us-central1
#   GOOGLE_GENAI_USE_VERTEXAI=TRUE
#   GOOGLE_ADK_MODEL=gemini-2.5-flash-lite
#
# Optional:
#   AGENT_ENGINE_STAGING_BUCKET=gs://your-staging-bucket
#
# The Google Agent Platform SDK has evolved across previews, so this helper
# checks for the modern `vertexai.agent_engines` module first and falls back to
# the older preview Reasoning Engine API when available.
# =============================================================================

from __future__ import annotations

import os
from pathlib import Path

import cloudpickle
import agent_engine_app

cloudpickle.register_pickle_by_value(agent_engine_app)

root_agent = agent_engine_app.root_agent


def _load_local_env():
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _project() -> str:
    value = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not value:
        raise RuntimeError("Set GOOGLE_CLOUD_PROJECT before deploying the agent.")
    return value


def _location() -> str:
    return os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")


def _requirements() -> list[str]:
    requirements_path = Path(__file__).resolve().parent / "requirements.txt"
    lines = requirements_path.read_text(encoding="utf-8-sig").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def _extra_packages() -> list[str]:
    return []


def _env_vars() -> dict[str, str]:
    keys = [
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_ADK_MODEL",
        "SHIFTIQ_BACKEND_URL",
        "SHIFTIQ_USE_MCP_TOOLS",
        "SHIFTIQ_ADK_TIMEOUT_SECONDS",
    ]
    return {key: os.getenv(key) for key in keys if os.getenv(key)}


def deploy():
    _load_local_env()

    import vertexai

    staging_bucket = os.getenv("AGENT_ENGINE_STAGING_BUCKET")
    vertexai.init(project=_project(), location=_location(), staging_bucket=staging_bucket)

    try:
        from vertexai import agent_engines
    except (ImportError, AttributeError):
        from vertexai.preview import reasoning_engines

        remote_agent = reasoning_engines.ReasoningEngine.create(
            root_agent,
            requirements=_requirements(),
            extra_packages=_extra_packages(),
            display_name="ShiftIQ Core Orchestrator",
            description="ADK multi-agent orchestrator for ShiftIQ scheduling, labor, coverage, weather, and policy tools.",
        )
    else:
        remote_agent = agent_engines.create(
            root_agent,
            requirements=_requirements(),
            extra_packages=_extra_packages(),
            env_vars=_env_vars(),
            display_name="ShiftIQ Core Orchestrator",
            description="ADK multi-agent orchestrator for ShiftIQ scheduling, labor, coverage, weather, and policy tools.",
        )

    print("Deployed ShiftIQ ADK agent:")
    print(remote_agent)
    return remote_agent


if __name__ == "__main__":
    deploy()
