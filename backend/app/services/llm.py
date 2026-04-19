"""
LLM triage + report service.

Primary:  Groq  (cloud, free tier) — set GROQ_API_KEY in .env
          https://api.groq.com/openai/v1/chat/completions
Fallback: Ollama (local)           — requires `ollama pull mistral`
"""
import json
import re
import httpx
from app.config import settings
from app.models.schemas import TriageResult

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are S.H.I.E.L.D — an AI dispatch assistant for Certis security officers.

Your job is to triage spoken officer reports and return a structured JSON response.

Rules:
- priority: "high" (immediate threat/safety risk), "medium" (requires attention soon), "low" (routine)
- category: "patrol" (routine checks), "incident" (active event needing response), "admin" (paperwork/scheduling)
- action: a clear, specific instruction for the officer (max 15 words)
- summary: a concise 1-sentence summary of the report (max 20 words)
- escalation_required: true if the situation involves weapons, medical emergency, officer outnumbered, hostage, or exceeds Certis authority; otherwise false
- escalation_reason: brief reason for escalation (1 sentence), or null if not required
- severity_flags: list of applicable tags from: ["armed_suspect", "medical_emergency", "outnumbered", "hostage", "spf_required"]; empty array if none apply
- requires_supervisor: true if Certis command or SPF must be notified; otherwise false
- missing_fields: list of field names that the officer's report did not provide. Possible values: ["location", "time", "persons_involved", "incident_type"]. Only include a field if it is genuinely absent. Return [] if all fields are present.
- If the officer is answering a follow-up question about an ongoing incident (evident from conversation history), merge the new information into the existing triage and return a complete updated JSON — do NOT start a fresh triage.
- If the officer says phrases like "new case", "new incident", "next report", or similar, treat this as a completely new independent triage; do not carry over any prior incident details.

ALWAYS respond with ONLY valid JSON in this exact format:
{
  "priority": "high|medium|low",
  "action": "...",
  "category": "patrol|incident|admin",
  "summary": "...",
  "escalation_required": true|false,
  "escalation_reason": "..." or null,
  "severity_flags": [],
  "requires_supervisor": true|false,
  "missing_fields": []
}

Do not include any explanation, preamble, or markdown. Only the JSON object."""


REPORT_SYSTEM_PROMPT = """You are S.H.I.E.L.D — an AI report writer for Certis security officers.

Your job is to generate a formal, compliance-ready incident report from a triage summary.

Rules:
- incident_type: a concise label (e.g. "Theft", "Trespass", "Assault", "Suspicious Activity")
- location: best-guess location from the summary, or "Not specified" if absent
- description: 2-3 sentence factual account of the incident
- actions_taken: 1-2 sentences on what the officer did or should do
- persons_involved: list of person descriptors mentioned (e.g. ["Male suspect, black hoodie"])
- evidence: list of evidence items mentioned (e.g. ["CCTV footage", "Officer testimony"])
- follow_up_required: true if further investigation or SPF handoff is needed

ALWAYS respond with ONLY valid JSON in this exact format:
{
  "incident_type": "...",
  "location": "...",
  "description": "...",
  "actions_taken": "...",
  "persons_involved": [],
  "evidence": [],
  "follow_up_required": true|false
}

Do not include any explanation, preamble, or markdown. Only the JSON object."""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_MISSING = {"location", "time", "persons_involved", "incident_type"}


def _parse_missing_fields(raw: list) -> list:
    if not isinstance(raw, list):
        return []
    return [f for f in raw if f in _VALID_MISSING]


def _extract_json(raw: str) -> dict:
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)
    return json.loads(raw)

# ---------------------------------------------------------------------------
# Backend: Groq (OpenAI-compatible chat completions)
# ---------------------------------------------------------------------------

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


async def _groq_call(
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    history: list | None = None,
) -> str:
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user})
    payload = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(_GROQ_URL, headers=headers, json=payload)
        response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# ---------------------------------------------------------------------------
# Backend: Ollama (local fallback)
# ---------------------------------------------------------------------------

async def _ollama_call(system: str, user: str, temperature: float, num_predict: int) -> str:
    payload = {
        "model": settings.ollama_model,
        "prompt": user,
        "system": system,
        "stream": False,
        "format": "json",
        "options": {"temperature": temperature, "num_predict": num_predict},
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate", json=payload
        )
        response.raise_for_status()
    return response.json().get("response", "").strip()

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def triage_transcript(transcript: str, history: list | None = None) -> TriageResult:
    """Triage a spoken officer report via Groq (or Ollama fallback)."""
    user = f"Officer report: {transcript}"

    if settings.groq_api_key:
        raw = await _groq_call(SYSTEM_PROMPT, user, temperature=0.2, max_tokens=256, history=history)
    else:
        raw = await _ollama_call(SYSTEM_PROMPT, user, temperature=0.2, num_predict=256)

    parsed = _extract_json(raw)

    priority = parsed.get("priority", "low")
    if priority not in ("high", "medium", "low"):
        priority = "low"

    category = parsed.get("category", "patrol")
    if category not in ("patrol", "incident", "admin"):
        category = "patrol"

    valid_flags = {"armed_suspect", "medical_emergency", "outnumbered", "hostage", "spf_required"}
    raw_flags = parsed.get("severity_flags", [])
    severity_flags = [f for f in raw_flags if f in valid_flags] if isinstance(raw_flags, list) else []

    return TriageResult(
        priority=priority,
        action=parsed.get("action", "Follow standard protocol."),
        category=category,
        summary=parsed.get("summary", transcript[:100]),
        escalation_required=bool(parsed.get("escalation_required", False)),
        escalation_reason=parsed.get("escalation_reason") or None,
        severity_flags=severity_flags,
        requires_supervisor=bool(parsed.get("requires_supervisor", False)),
        missing_fields=_parse_missing_fields(parsed.get("missing_fields", [])),
    )


async def generate_report(summary: str, action: str, severity_flags: list) -> dict:
    """Generate a structured incident report dict from triage data."""
    user = (
        f"Triage summary: {summary}\n"
        f"Action taken/required: {action}\n"
        f"Severity flags: {', '.join(severity_flags) if severity_flags else 'none'}"
    )

    if settings.groq_api_key:
        raw = await _groq_call(REPORT_SYSTEM_PROMPT, user, temperature=0.1, max_tokens=400)
    else:
        raw = await _ollama_call(REPORT_SYSTEM_PROMPT, user, temperature=0.1, num_predict=400)

    return _extract_json(raw)
