# ShiftIQ - POS Scheduling Agent

ShiftIQ is a full-stack hackathon MVP that turns sample POS data into sales insights, demand forecasts, optimized employee schedules, call-out backup recommendations, and data-grounded manager chat.

For the Google for Startups AI Agents Challenge, ShiftIQ is structured as a Track 1 multi-agent system using Google ADK, Vertex AI Gemini, MCP tool access, and Cloud Run deployment scaffolding.

The original static prototype is preserved at `docs/reference-demo.html`.

## Project Structure

```text
backend/   FastAPI API and agent modules
frontend/  React/Vite dashboard
data/      CSV sample data
docs/      Reference static demo
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

Open `http://localhost:5173`. The `dev` command builds the React app and serves the production bundle with a small Node server to avoid Vite's Windows child-process issue in restricted environments.

## Google ADK Manager Chat

Manager Chat works without an API key using deterministic data-grounded fallback responses, but the primary path uses Google ADK with Vertex AI Gemini.

Local Vertex AI configuration lives in `backend/.env`:

```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_ADK_MODEL=gemini-2.5-flash-lite
```

The chat page includes a selectable ADK agent team:

- Core Orchestrator
- Tool Calling Agent
- Schedule Explanation Agent
- Call-Out & Coverage Agent
- Labor Optimization Agent
- Report & Export Agent

## MCP Server

ShiftIQ exposes its business tools through a local MCP server:

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

1. Open Sales Insights and point out Friday/Saturday peaks.
2. Open Forecast and show next-week demand.
3. Open Employees and send availability requests.
4. Open Schedule and generate an optimized schedule.
5. Show the assignment explanations and labor monitor.
6. Open Call-out Manager, find backups, and confirm the top candidate.
7. Return to Schedule and verify the replacement assignment.
8. Ask Manager Chat: `How can I reduce labor by $200 this week?`

## Key API Endpoints

- `GET /health`
- `GET /employees`
- `GET /insights/summary`
- `GET /insights/daily-revenue`
- `GET /insights/heatmap`
- `GET /insights/top-items`
- `GET /forecast/next-week`
- `POST /schedule/generate`
- `GET /schedule/current`
- `GET /labor/summary`
- `POST /messaging/request-availability`
- `POST /callouts/find-backups`
- `POST /callouts/confirm-backup`
- `POST /chat`
