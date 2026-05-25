# ShiftIQ - POS Scheduling Agent

ShiftIQ is a full-stack hackathon MVP that turns sample POS data into sales insights, demand forecasts, optimized employee schedules, call-out backup recommendations, and data-grounded manager chat.

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

## Optional AI Chat

Manager Chat works without an API key using deterministic data-grounded fallback responses.

To enable OpenAI-backed answers:

```bash
set OPENAI_API_KEY=your_key_here
```

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
