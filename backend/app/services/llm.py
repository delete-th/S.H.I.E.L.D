"""
LLM triage service using Ollama + Mistral (free, open-source).

Ollama runs locally (or in Docker) and exposes a REST API at port 11434.
Model: mistral (default) — configurable via OLLAMA_MODEL env var.

To pull the model:
  docker exec -it certis-shield-ollama-1 ollama pull mistral
  # or locally:
  ollama pull mistral
"""
import json
import re
import httpx
from app.config import settings
from app.models.schemas import TriageResult

SYSTEM_PROMPT = """You are S.H.I.E.L.D — an AI dispatch assistant for Certis security officers.

Your job is to triage spoken officer reports and return a structured JSON response.

Rules:
- priority: "high" (immediate threat/safety risk), "medium" (requires attention soon), "low" (routine)
- category: "patrol" (routine checks), "incident" (active event needing response), "admin" (paperwork/scheduling)
- action: a clear, specific instruction for the officer (max 15 words)
- summary: a concise 1-sentence summary of the report (max 20 words)

ALWAYS respond with ONLY valid JSON in this exact format:
{
  "priority": "high|medium|low",
  "action": "...",
  "category": "patrol|incident|admin",
  "summary": "..."
}

Do not include any explanation, preamble, or markdown. Only the JSON object."""


async def triage_transcript(transcript: str) -> TriageResult:
    """Send transcript to Ollama/Mistral and parse structured triage JSON."""
    prompt = f"Officer report: {transcript}"

    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "num_predict": 256,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    raw = data.get("response", "").strip()

    # Extract JSON if wrapped in markdown code blocks
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)

    parsed = json.loads(raw)

    # Validate and coerce fields
    priority = parsed.get("priority", "low")
    if priority not in ("high", "medium", "low"):
        priority = "low"

    category = parsed.get("category", "patrol")
    if category not in ("patrol", "incident", "admin"):
        category = "patrol"

    return TriageResult(
        priority=priority,
        action=parsed.get("action", "Follow standard protocol."),
        category=category,
        summary=parsed.get("summary", transcript[:100]),
    )
