# S.H.I.E.L.D — AI Walkie Talkie for Certis Security Officers

**Streamlined Handling of Incidents, Emergencies, and Logistics Dispatch**

An AI-powered push-to-talk system that triages patrol reports in real time, reducing cognitive load for Certis security officers.

## Architecture

```
Officer speaks → WebSocket audio stream → Whisper STT → Mistral (Ollama) triage → ElevenLabs TTS → Officer hears response
```

- **Frontend**: React + Vite + Tailwind, WebSocket audio streaming
- **Backend**: FastAPI, Whisper STT, Ollama/Mistral (free LLM), ElevenLabs TTS, Redis cache
- **Database**: Supabase (Postgres)

## Quick Start

### 1. Prerequisites
- Docker + Docker Compose
- Node.js 18+
- Python 3.11+

### 2. Clone & configure
```bash
cp .env.example .env
# Fill in ELEVENLABS_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY
```

### 3. Start backend services
```bash
docker compose up -d

# Pull the Mistral model into Ollama (first time only, ~4GB)
docker exec -it certis-shield-ollama-1 ollama pull mistral
```

### 4. Start frontend
```bash
cd frontend
npm install
npm run dev
```

### 5. (Optional) Run backend locally without Docker
```bash
cd backend
pip install -r requirements.txt

# Make sure Redis and Ollama are running, then:
uvicorn main:app --reload --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| WS | `/ws/audio` | Stream mic audio, receive TTS response |
| POST | `/triage` | Triage a text transcript |
| GET | `/tasks` | List patrol tasks |
| POST | `/tasks` | Create a task |
| DELETE | `/tasks/{id}` | Delete a task |

## Triage Response Schema

```json
{
  "priority": "high | medium | low",
  "action": "Dispatch backup to Gate B immediately",
  "category": "patrol | incident | admin",
  "summary": "Officer reports suspicious individual near Gate B"
}
```

## LLM: Ollama + Mistral (Free & Open Source)

S.H.I.E.L.D uses [Ollama](https://ollama.ai) with **Mistral 7B** for triage — no API costs, runs fully on-premise. Change `OLLAMA_MODEL` in `.env` to use `llama3.2`, `gemma2`, or any Ollama-supported model.

## Database Schema

See `supabase/migrations/001_init.sql` for the full schema (officers, tasks, incidents tables).
