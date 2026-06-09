# Google AI Studio Gemini API Key Setup

This note preserves the direct Google AI Studio Gemini API setup path for ShiftIQ Manager Chat.

## When To Use This

Use this path when you want the fastest local setup with a Google AI Studio API key.

This is different from Vertex AI. The AI Studio path uses `GOOGLE_API_KEY` directly and may require Gemini API prepay credits in AI Studio billing.

## Required Backend Environment

Create or update:

```text
backend/.env
```

Add:

```env
GOOGLE_API_KEY=your_google_ai_studio_key_here
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_ADK_MODEL=gemini-3.1-flash-lite
```

`GOOGLE_ADK_MODEL` is optional because ShiftIQ already defaults to `gemini-3.1-flash-lite`.

## Billing Notes

If Manager Chat reaches Google but falls back locally, check the backend/API error. A `429 RESOURCE_EXHAUSTED` response usually means the AI Studio Gemini API key is valid but the associated project has no usable Gemini API credits.

To fix that path:

1. Open Google AI Studio billing.
2. Select the project tied to the API key.
3. Add Gemini API prepay credits if required.
4. Restart the FastAPI backend.

## Local Run Commands

Backend:

```bash
cd backend
python -m uvicorn main:app --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

Then test Manager Chat from the app or call:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"What are my busiest hours?\",\"history\":[]}"
```

