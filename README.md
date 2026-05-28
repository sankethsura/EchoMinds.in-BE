# EchoMinds — Backend

FastAPI token server + LiveKit voice agent (Aria).

## Prerequisites

- Python 3.11+
- A [LiveKit Cloud](https://livekit.io) project (free tier works)
- OpenAI API key
- Deepgram API key (free tier works)

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
```

## Environment Variables

| Variable | Description |
|---|---|
| `LIVEKIT_URL` | Your LiveKit server WebSocket URL (e.g. `wss://xxx.livekit.cloud`) |
| `LIVEKIT_API_KEY` | LiveKit project API key |
| `LIVEKIT_API_SECRET` | LiveKit project API secret |
| `OPENAI_API_KEY` | OpenAI API key (used for LLM + TTS) |
| `DEEPGRAM_API_KEY` | Deepgram API key (used for STT) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins (default: `http://localhost:3000`) |

## Running

You need **two terminals** — the API server and the agent worker.

**Terminal 1 — API server:**
```bash
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Agent worker:**
```bash
source .venv/bin/activate
python agent.py dev
```

The agent worker connects to LiveKit and waits for room participants. When the frontend joins a room, LiveKit dispatches a job to the agent which then joins the same room.

## Endpoints

- `GET /health` — health check
- `GET /token?room=<name>&participant=<identity>` — returns a LiveKit JWT
# EchoMinds.in-BE
