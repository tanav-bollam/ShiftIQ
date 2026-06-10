# ShiftIQ Track 1 Architecture

ShiftIQ is a Track 1 net-new agent system for workforce and labor optimization. It helps small food and retail businesses convert POS history, employee availability, labor guardrails, weather context, and shift events into safer staffing actions.

## Why Multi-Agent Instead Of One Chatbot

A single chatbot can answer broad questions, but it tends to blur together data lookup, scheduling logic, labor policy, coverage decisions, and business explanations. ShiftIQ separates those responsibilities into an agent team:

- Core Orchestrator: understands manager intent and coordinates the specialist agents.
- Tool Calling Agent: retrieves exact live data through tools instead of relying on model memory.
- Schedule Explanation Agent: explains why people were assigned and what constraints mattered.
- Call-Out & Coverage Agent: ranks replacement candidates for dropped shifts and call-outs.
- Labor Optimization Agent: recommends labor-saving actions against revenue and target percentages.
- Report & Export Agent: creates schedule and labor report artifacts.
- Policy Knowledge Agent: retrieves written operating rules before answering approval, fairness, and shift-policy questions.

This design makes the system easier to explain, test, and govern. Each specialist has a narrower job, and risky actions are routed through approval and audit workflows.

## ADK Orchestration

The manager chat uses Google ADK `LlmAgent` profiles. The root agent is exported from `backend/agent_engine_app.py` for Agent Runtime / Agent Engine deployment.

ADK capabilities used:

- `LlmAgent` for Gemini-backed reasoning.
- Agent profiles for specialist behavior.
- Sessions for multi-turn context.
- Tool callbacks for audit logging.
- Artifacts for generated schedule and labor reports.
- MCP toolset integration for standardized tool access.

## MCP Tool Layer

ShiftIQ exposes operational capabilities through `backend/mcp_server.py`. The ADK registry in `backend/agents/mcp_registry.py` creates an MCP toolset that includes:

- schedule generation
- current schedule lookup
- labor summary
- sales insights
- employee profile lookup
- schedule explanation
- backup candidate ranking
- labor optimization
- weather-aware staffing
- policy knowledge search
- report artifact creation

The Manager Chat path prefers MCP tools when `SHIFTIQ_USE_MCP_TOOLS` is enabled and falls back to direct Python function tools for local demo reliability.

## Grounding And RAG

ShiftIQ includes a local policy knowledge base in `data/knowledge`. The Policy Knowledge Agent searches these documents and returns cited excerpts.

Current knowledge documents:

- scheduling policy
- shift coverage and call-out policy
- weather-aware staffing policy

This is a lightweight custom RAG layer for the MVP. The same tool boundary can be upgraded to Vertex AI Search, Agent Platform Search, or RAG Engine without changing the frontend workflow.

## Autonomous Actions With Governance

The agent can do more than report information. It can:

- create schedule-mode approval requests
- generate block or flexible schedules after approval
- recommend backup candidates
- create report artifacts
- explain labor-saving recommendations
- retrieve policy citations

Risky actions are not silently executed. Schedule-regeneration requests create approval records that managers review on the Agent Actions page. Approved actions are logged and persisted.

## Data And Persistence

ShiftIQ uses:

- CSV sample data for POS sales, employees, availability, and role requirements.
- SQLite for runtime state, audit events, and approvals.
- Open-Meteo for weather forecasts.
- In-app generated state for schedule and shift events.

## Google Cloud Deployment

The web app is deployed on Cloud Run:

- FastAPI backend container
- React/Nginx frontend container
- Cloud Build pipeline
- Artifact Registry images

The ADK root agent is prepared for Agent Runtime / Agent Engine through `backend/agent_engine_app.py` and `backend/deploy_agent_engine.py`.

## Submission Narrative

ShiftIQ demonstrates a practical business agent that takes declarative manager intent such as “generate a flexible demand schedule” or “who should cover Sarah’s shift” and turns it into grounded, auditable workflows. Multi-agent collaboration matters because scheduling requires live data access, policy retrieval, explainable decisions, and approval-gated action, not just conversational fluency.
