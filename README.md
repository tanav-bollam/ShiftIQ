# ShiftIQ - AI Workforce Scheduling Agent

ShiftIQ is a full-stack hackathon MVP for small food and retail businesses. It connects POS-style sales data, employee availability, labor targets, weather context, and real-time staffing events so managers can build better schedules, reduce labor waste, and handle call-outs faster.

For the Google for Startups AI Agents Challenge, ShiftIQ is structured as a Track 1 net-new multi-agent system using Google ADK concepts, Vertex AI Gemini, MCP tool access, grounding/RAG, and Cloud Run deployment.

## Live Demo

- Frontend: https://shiftiq-frontend-y5d7huc3pq-uc.a.run.app
- Backend health: https://shiftiq-backend-y5d7huc3pq-uc.a.run.app/health
- Architecture page: https://shiftiq-frontend-y5d7huc3pq-uc.a.run.app/architecture.html
- Presentation: https://docs.google.com/presentation/d/1wg7Xshr33yIe9LxRHwDhoamGmP9YGxqf5lVcdaDVC3Q
- Video Presentation: https://www.youtube.com/watch?v=an9kXEFnLY8&feature=youtu.be

## Current Features

- Sales insights from CSV-backed POS data
- Daily revenue cards, busiest periods, top items, and hourly heatmap
- Demand forecast by day
- Weather-aware forecast and staffing recommendations
- Labor cost summary with green/amber/red guardrails
- Staffing threshold controls for demand-based employee counts
- Traditional shift-block schedule generation
- Flexible demand-based schedule generation
- Manual schedule editing
- Employee roster with skills, wages, max hours, status, and call-out history
- Employee portal with selected employee identity
- Employee-specific messages and notifications
- Weekly availability with specific start/end hours
- Shift drop, open shift, claim, approval, and auto-approval workflows
- Call-out backup ranking and confirmation
- Data upload, validation preview, and editable CSV-backed data tables
- Agent approval workflow for high-impact actions
- Audit log for manager and agent actions
- Manager Chat with selectable agent modes
- Local deterministic chat fallback when external AI credentials are unavailable
- Lightweight policy RAG over `data/knowledge`
- Local MCP server exposing ShiftIQ tools
- Cloud Run deployment scaffolding

## Project Structure

```text
backend/   FastAPI API, agent modules, MCP server, ADK/Agent Engine helpers
frontend/  React/Vite dashboard and employee portal
data/      CSV sample data and local knowledge documents
docs/      Reference demo, architecture docs, and standalone architecture site
```

## Start The Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`.

## Start The Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

The `dev` command builds the React app and serves the production bundle with `server.mjs`. This avoids Vite's Windows child-process issue in restricted environments.

## Local Environment

Secrets stay local in `backend/.env`, which is ignored by Git.

Vertex AI configuration:

```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_ADK_MODEL=gemini-2.5-flash-lite
```

Google AI Studio key mode is documented at `docs/google-ai-studio-gemini-api-key.md`.

Manager Chat still works without external credentials by using deterministic, data-grounded fallback responses.

## Manager Chat And Agent Team

The chat page includes a selectable agent team:

- Core Orchestrator
- Tool Calling Agent
- Schedule Explanation Agent
- Call-Out & Coverage Agent
- Labor Optimization Agent
- Report & Export Agent
- Policy Knowledge Agent

The Core Orchestrator routes manager intent to specialized tools and agents. The assistant can answer questions, explain schedules, find backup candidates, recommend labor savings, create approval requests, and consult policy knowledge.

## MCP Server

ShiftIQ exposes business tools through a local MCP server:

```bash
cd backend
python mcp_server.py
```

HTTP MCP mode:

```bash
cd backend
python mcp_server.py --transport http --host 0.0.0.0 --port 8010
```

The ADK MCP toolset configuration is in `backend/agents/mcp_registry.py`.

Manager Chat prefers the MCP toolset when ADK is enabled. To force direct local function tools for debugging:

```env
SHIFTIQ_USE_MCP_TOOLS=FALSE
```

## Grounding And RAG

ShiftIQ includes a lightweight policy RAG layer in `data/knowledge`. The Policy Knowledge Agent retrieves cited policy excerpts for approval, fairness, dropped-shift, and weather-staffing questions.

Useful endpoints:

- `GET /knowledge/overview`
- `GET /knowledge/search?q=manager approval`

This local RAG layer can later be swapped for Vertex AI Search, Agent Platform Search, or RAG Engine.

## Agent Engine / Agent Runtime

The ADK root agent is exported from `backend/agent_engine_app.py` as `root_agent`.

Deployment helper:

```bash
cd backend
python deploy_agent_engine.py
```

Required environment:

```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_ADK_MODEL=gemini-2.5-flash-lite
AGENT_ENGINE_STAGING_BUCKET=gs://optional-staging-bucket
```

Architecture details:

- `docs/track-1-architecture.md`
- `docs/architecture.html`
- frontend route `/architecture`

## Google Cloud Deployment

Cloud Run deployment scaffolding is included:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `cloudbuild.yaml`

Deploy:

```bash
gcloud artifacts repositories create shiftiq --repository-format=docker --location=us-central1
gcloud builds submit --config cloudbuild.yaml
```

More detail: `docs/track-1-production-readiness.md`.

## Demo Flow

1. Open the dashboard and show the live labor gauge.
2. Open Sales Insights and point out Friday/Saturday peaks.
3. Hover the hourly heatmap to show revenue/intensity details.
4. Open Forecast and show next-week demand.
5. Open the weather-aware forecast recommendation.
6. Open Employees and show skills, max hours, scheduled hours, and exact availability windows.
7. Open Data Manager to show editable CSV-backed business data.
8. Open Schedule and generate an optimized block schedule.
9. Switch to flexible demand scheduling and regenerate.
10. Show assignment explanations and daily labor monitor.
11. Manually edit a shift assignment.
12. Open the employee portal, select an employee, and submit hourly availability.
13. Drop or request a shift swap.
14. Show employee-specific messages and notifications.
15. Open Call-out Manager, find backups, and confirm the top candidate.
16. Open Agent Actions and show approvals/auditability.
17. Ask Manager Chat: `How can I reduce labor by $200 this week?`
18. Open Architecture to explain ADK, MCP, RAG, approvals, and Cloud Run.

## Key API Endpoints

- `GET /health`
- `GET /employees`
- `GET /roles`
- `GET /staffing-thresholds`
- `PUT /staffing-thresholds`
- `GET /data-tables/{file_type}`
- `PUT /data-tables/{file_type}`
- `POST /upload/{file_type}`
- `POST /upload/{file_type}/preview`
- `GET /insights/summary`
- `GET /insights/daily-revenue`
- `GET /insights/heatmap`
- `GET /insights/busiest`
- `GET /insights/top-items`
- `GET /insights/overstaffing`
- `GET /forecast/next-week`
- `GET /forecast/weather-aware`
- `POST /schedule/generate`
- `GET /schedule/current`
- `POST /schedule/edit-shift`
- `GET /labor/summary`
- `GET /employee/shift-requests`
- `POST /employee/shift-requests`
- `POST /employee/shift-requests/{request_id}/claim`
- `POST /employee/shift-requests/{request_id}/approve`
- `POST /messaging/request-availability`
- `POST /employee/availability`
- `GET /messaging/log`
- `GET /notifications`
- `GET /audit-log`
- `GET /knowledge/overview`
- `GET /knowledge/search`
- `GET /agent-approvals`
- `POST /agent-approvals/{approval_id}/approve`
- `POST /agent-approvals/{approval_id}/reject`
- `POST /callouts/find-backups`
- `POST /callouts/confirm-backup`
- `POST /chat`
- `GET /chat/agents`
- `GET /chat/artifacts`
- `GET /chat/artifacts/{filename}`

## Verification

Common local checks:

```bash
cd frontend
npm run build
```

```bash
python -m compileall backend
```

The app has been audited against the live Cloud Run deployment for route rendering, frontend console errors, backend API responses, schedule generation, chat fallback, employee-specific messages, and architecture pages.
