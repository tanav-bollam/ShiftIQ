# ShiftIQ Track 1 Production Readiness

ShiftIQ is positioned for the Google for Startups AI Agents Challenge Track 1: Build.

## What Is Now Addressed

### 1. MCP Tool Access

ShiftIQ now includes a local Model Context Protocol server:

```text
backend/mcp_server.py
```

It exposes the core business tools that the ADK agent team needs:

- `get_shift_iq_overview`
- `get_labor_summary_tool`
- `get_current_schedule_tool`
- `get_sales_insights_tool`
- `get_employee_profile_tool`
- `explain_schedule_assignment_tool`
- `generate_schedule_tool`
- `find_backup_candidates_tool`
- `optimize_labor_savings_tool`
- `create_report_artifact_tool`

Run it locally over stdio:

```bash
cd backend
python mcp_server.py
```

Run it over streamable HTTP:

```bash
cd backend
python mcp_server.py --transport http --host 0.0.0.0 --port 8010
```

ADK integration point:

```text
backend/agents/mcp_registry.py
```

That file builds a `McpToolset` from the local MCP server so the ADK agent system can migrate from direct Python function tools to MCP-hosted tools when deployed.

### 2. Google Cloud Deployment

The repo now includes Cloud Run build/deploy scaffolding:

```text
backend/Dockerfile
frontend/Dockerfile
frontend/nginx.conf
cloudbuild.yaml
```

Expected deployment target:

- Backend: Cloud Run service `shiftiq-backend`
- Frontend: Cloud Run service `shiftiq-frontend`
- Model access: Vertex AI through Application Default Credentials / Cloud Run service account
- Required backend env:

```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=<project-id>
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_ADK_MODEL=gemini-2.5-flash-lite
```

Build and deploy:

```bash
gcloud artifacts repositories create shiftiq \
  --repository-format=docker \
  --location=us-central1 \
  --description="ShiftIQ container images"

gcloud builds submit --config cloudbuild.yaml
```

### 3. Agent Engine Readiness

ShiftIQ already has a Google ADK agent team inside:

```text
backend/agents/assistant_agent.py
backend/agent_engine_app.py
```

Current agent team:

- Core Orchestrator
- Tool Calling Agent
- Schedule Explanation Agent
- Call-Out & Coverage Agent
- Labor Optimization Agent
- Report & Export Agent

ADK capabilities currently used:

- `LlmAgent`
- Function tools
- Sessions through `InMemorySessionService`
- Artifacts through `InMemoryArtifactService`
- Tool callbacks for tool-call logging

Agent Engine deployment path:

1. Use `backend/agent_engine_app.py`, which exports `root_agent`.
2. Replace in-memory services with durable managed equivalents where needed.
3. Use `mcp_registry.py` to expose ShiftIQ tools through `McpToolset`.
4. Deploy the ADK entrypoint to Agent Engine.
5. Keep the FastAPI backend as the application API, or let FastAPI call the hosted Agent Engine endpoint.

## Track 1 Story

ShiftIQ is a multi-agent operations manager for small retail and food businesses. It connects POS sales patterns, employee skills, availability, labor targets, schedule constraints, call-outs, and reporting into one agentic workflow.

Why multi-agent is stronger than one chatbot:

- The Core Orchestrator coordinates manager questions and actions.
- The Tool Calling Agent grounds answers in live ShiftIQ data.
- The Schedule Explanation Agent makes assignments transparent.
- The Coverage Agent responds to dropped shifts and call-outs.
- The Labor Agent finds savings and staffing tradeoffs.
- The Export Agent creates operational reports.

MCP gives the agent team a secure, inspectable tool boundary. The same MCP pattern can later connect to:

- real POS providers
- weather APIs
- payroll systems
- SMS/email messaging
- inventory systems
- Google Calendar or employee scheduling tools

## Remaining Production Hardening

- Move schedule/message runtime state to a database.
- Add authentication and role-based permissions.
- Restrict Cloud Run CORS to the frontend domain.
- Put secrets in Secret Manager.
- Add structured logging/tracing for ADK tool calls.
- Add automated backend tests for the MCP tools.
- Add a real POS/weather connector behind MCP.
- Add Agent Engine deployment command once the target project/environment is finalized.
