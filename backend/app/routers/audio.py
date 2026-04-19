"""
WebSocket endpoint: /ws/audio

Flow:
  1. Receive audio bytes → STT transcribe → check Redis cache → LLM triage → TTS synthesize → send back JSON + audio
  2. Auto-save task to Supabase
  3. Broadcast incident.alert to all officers if category == "incident"
  4. Send follow_up prompt if LLM detected missing fields
"""
import base64
import re
import uuid
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

def _as_uuid(value: Optional[str]) -> Optional[str]:
    """Return value only if it's a valid UUID, else None."""
    return value if (value and _UUID_RE.match(value)) else None
from app.services import stt, llm, tts, cache
from app.services.db import get_supabase
from app.websocket.manager import manager
from app.websocket.events import Events
from app.models.schemas import Task

router = APIRouter()

FOLLOW_UP_PROMPTS = {
    "location": "What is the location of the incident?",
    "time": "What time did this occur?",
    "persons_involved": "Can you describe the persons involved?",
    "incident_type": "What type of incident is this?",
}

# STT often mishears Singapore place names — correct before LLM + frontend see the text
_LOCATION_FIXES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bboogi[e']?s?\s+junction\b", re.I), "Bugis Junction"),
    (re.compile(r"\bbogi[e']?s?\b", re.I),              "Bugis"),
    (re.compile(r"\bdampines\b", re.I),                  "Tampines"),
    (re.compile(r"\bdam\s*pines\b", re.I),               "Tampines"),
    (re.compile(r"\btampin[gse]+\b", re.I),              "Tampines"),
    (re.compile(r"\bjur[ao]ng\b", re.I),                 "Jurong"),
    (re.compile(r"\bang\s+mo\s+k[ie]o\b", re.I),        "Ang Mo Kio"),
    (re.compile(r"\bpas[ei]r\s+r[ie]s\b", re.I),        "Pasir Ris"),
    (re.compile(r"\bwood\s*lands?\b", re.I),             "Woodlands"),
    (re.compile(r"\bseng\s*kang\b", re.I),               "Sengkang"),
    (re.compile(r"\bpung\s*gol\b", re.I),                "Punggol"),
    (re.compile(r"\borg\s*chard\b", re.I),               "Orchard"),
    (re.compile(r"\bchang[ie]\b", re.I),                 "Changi"),
    (re.compile(r"\byew\s*shun\b", re.I),                "Yishun"),
    (re.compile(r"\byee\s*shun\b", re.I),                "Yishun"),
    (re.compile(r"\bbed[ao]k\b", re.I),                  "Bedok"),
    (re.compile(r"\bclem[ae]nti\b", re.I),               "Clementi"),
    (re.compile(r"\btoa\s+pay[ao]h\b", re.I),            "Toa Payoh"),
    (re.compile(r"\braffl[ei]s\b", re.I),                "Raffles"),
    (re.compile(r"\bserang[ao]{2}n\b", re.I),            "Serangoon"),
    (re.compile(r"\bbishen\b", re.I),                    "Bishan"),
    (re.compile(r"\bchoa\s+chu\s+kang\b", re.I),        "Choa Chu Kang"),
    (re.compile(r"\bboon\s+lay\b", re.I),                "Boon Lay"),
    (re.compile(r"\bgay\s*lang\b", re.I),                "Geylang"),
    (re.compile(r"\bguy\s*lang\b", re.I),                "Geylang"),
]

# Matches "change/update/correct/set location to X" or "location is X"
_LOCATION_UPDATE_RE = re.compile(
    r'\b(?:change|update|correct|move|set)\s+(?:the\s+)?location\s+(?:to|is)\s+(.+?)(?:[,.]|$)',
    re.IGNORECASE,
)
_LOCATION_IS_RE = re.compile(
    r'\blocation\s+(?:is\s+)?(?:actually\s+|now\s+)?(?:at\s+)?(.+?)(?:[,.]|$)',
    re.IGNORECASE,
)


def _fix_location_names(text: str) -> str:
    for pattern, replacement in _LOCATION_FIXES:
        text = pattern.sub(replacement, text)
    return text


def _extract_forced_location(text: str) -> Optional[str]:
    m = _LOCATION_UPDATE_RE.search(text)
    if m:
        return m.group(1).strip()
    return None


_RESET_PHRASES = {"new case", "new incident", "next report", "new report", "fresh case", "start over"}

_INCIDENT_KEYWORDS = [
    ("robbery", "Robbery"), ("theft", "Theft"), ("shopli", "Shoplifting"),
    ("assault", "Assault"), ("fight", "Fight/Assault"),
    ("drug", "Drug-Related Activity"), ("trespass", "Trespassing"),
    ("suspicious", "Suspicious Activity"), ("vandal", "Vandalism"),
    ("fire", "Fire/Emergency"), ("medical", "Medical Emergency"),
    ("missing", "Missing Person"),
]


def _infer_incident_type(text: str) -> str:
    t = text.lower()
    for kw, label in _INCIDENT_KEYWORDS:
        if kw in t:
            return label
    return "General Incident"


def _update_report(
    report: dict,
    result,
    transcript: str,
    officer_id: Optional[str],
    now: datetime,
    forced_location: Optional[str] = None,
) -> dict:
    if not report.get("date"):
        report["date"] = now.strftime("%d %b %Y")
    if not report.get("time"):
        report["time"] = now.strftime("%H:%M")
    if not report.get("officer_badge"):
        report["officer_badge"] = officer_id or "—"

    report["severity"] = result.priority
    report["actions_taken"] = result.action

    # Don't pollute description with field-update commands
    is_update_command = forced_location is not None
    if not is_update_command:
        prev = report.get("description", "")
        report["description"] = f"{prev} {transcript}".strip() if prev else transcript

    if not report.get("incident_type"):
        report["incident_type"] = (
            result.incident_type
            or _infer_incident_type(f"{transcript} {result.summary}")
        )

    # Forced location (from "change location to X") overrides existing value
    if forced_location:
        report["location"] = forced_location
    elif result.location and not report.get("location"):
        report["location"] = result.location

    missing = set(result.missing_fields)
    # Only set persons_involved if LLM actually extracted a complete description
    if result.persons_involved and not report.get("persons_involved"):
        report["persons_involved"] = result.persons_involved
    if "time" not in missing and not report.get("incident_time"):
        report["incident_time"] = "Mentioned in report"

    report["pending_fields"] = result.missing_fields
    report["status"] = "draft"
    return report


def _build_follow_up_text(missing_fields: list, follow_up_questions: dict | None = None) -> str:
    parts = []
    for f in missing_fields:
        # Prefer LLM-generated contextual question, fall back to static prompt
        q = (follow_up_questions or {}).get(f) or FOLLOW_UP_PROMPTS.get(f)
        if q:
            parts.append(q)
    return " ".join(parts)


def _is_reset_phrase(transcript: str) -> bool:
    t = transcript.lower().strip()
    return any(phrase in t for phrase in _RESET_PHRASES)


@router.websocket("/ws/audio")
async def audio_websocket(
    websocket: WebSocket,
    officer_id: Optional[str] = Query(default=None),
):
    await websocket.accept()
    print(f"[WS] Client connected. officer_id={officer_id}")

    conversation_history: list[dict] = []
    current_report: dict = {}

    try:
        while True:
            audio_bytes = await websocket.receive_bytes()
            if not audio_bytes:
                continue

            # Step 1: Transcribe + normalize Singapore location names
            try:
                transcript = await stt.transcribe(audio_bytes)
            except Exception as e:
                await websocket.send_json({"type": "error", "message": f"STT failed: {e}"})
                continue

            if not transcript:
                await websocket.send_json({"type": "error", "message": "No speech detected."})
                continue

            forced_location = _extract_forced_location(transcript)

            # Step 2: LLM triage — do this before sending transcript so we can
            # send the AI-corrected version to the frontend chat
            result = await cache.get_cached(transcript)
            if result is None:
                try:
                    result = await llm.triage_transcript(transcript, history=conversation_history)
                    await cache.set_cached(transcript, result)
                except Exception as e:
                    await websocket.send_json({"type": "transcript", "text": transcript})
                    await websocket.send_json({"type": "error", "message": f"LLM failed: {e}"})
                    continue

            # Send corrected transcript to frontend (falls back to raw if LLM returned none)
            display_transcript = result.corrected_transcript or transcript
            await websocket.send_json({"type": "transcript", "text": display_transcript})

            # Reset conversation if officer signals a new case (phrase OR LLM intent detection)
            if _is_reset_phrase(transcript) or result.is_new_case:
                conversation_history.clear()
                if current_report.get("description"):
                    finalized = {**current_report, "status": "finalized"}
                    await websocket.send_json({"type": "report_finalized", "report": finalized})
                    try:
                        sb = get_supabase()
                        sb.table("tasks").insert({
                            "t_priority": current_report.get("severity", "low"),
                            "t_category": "incident",
                            "t_action": current_report.get("actions_taken", "Report finalized"),
                            "t_summary": current_report.get("description", "")[:200],
                            "t_created_at": datetime.utcnow().isoformat(),
                        }).execute()
                    except Exception as e:
                        print(f"[Report] Save failed (non-fatal): {e}")
                current_report = {}
                await websocket.send_json({"type": "conversation_reset"})

            # Append to conversation history (cap at 10 messages / 5 turns)
            conversation_history.append({"role": "user", "content": f"Officer report: {display_transcript}"})
            conversation_history.append({"role": "assistant", "content": result.model_dump_json()})
            if len(conversation_history) > 10:
                conversation_history = conversation_history[-10:]

            tts_text = tts.build_tts_text(result)
            await websocket.send_json({"type": "triage", "result": result.model_dump(), "tts_text": tts_text})

            # Update live incident report accumulator
            if result.category == "incident" or forced_location:
                _update_report(current_report, result, display_transcript, officer_id, datetime.utcnow(), forced_location)
                await websocket.send_json({"type": "report_update", "report": current_report})

            # Step 3: Auto-save task to Supabase
            task_id = str(uuid.uuid4())
            try:
                task = Task(
                    t_id=task_id,
                    t_officer_id=_as_uuid(officer_id),
                    t_priority=result.priority,
                    t_category=result.category,
                    t_action=result.action,
                    t_summary=result.summary,
                    t_created_at=datetime.utcnow(),
                    t_escalation_required=result.escalation_required,
                    t_escalation_reason=result.escalation_reason,
                    t_severity_flags=result.severity_flags,
                    t_requires_supervisor=result.requires_supervisor,
                    t_escalated_at=datetime.utcnow() if result.escalation_required else None,
                )
                sb = get_supabase()
                res = sb.table("tasks").insert(
                    task.model_dump(by_alias=True, mode="json", exclude_none=True)
                ).execute()
                if res.data:
                    task_id = res.data[0].get("t_id", task_id)
            except Exception as e:
                print(f"[WS] Supabase insert failed (non-fatal): {e}")

            # Step 4: Broadcast incident.alert to all officers
            if result.category == "incident":
                try:
                    await manager.broadcast({
                        "event": Events.INCIDENT_ALERT,
                        "task_id": task_id,
                        "officer_id": officer_id,
                        "priority": result.priority,
                        "summary": result.summary,
                        "action": result.action,
                        "severity_flags": result.severity_flags,
                        "escalation_required": result.escalation_required,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                except Exception as e:
                    print(f"[WS] Broadcast failed (non-fatal): {e}")

            # Step 5: TTS — single-request for clean, artifact-free audio
            try:
                audio_data = await tts.synthesize(tts_text)
                if audio_data:
                    await websocket.send_json({
                        "type": "audio",
                        "data": base64.b64encode(audio_data).decode(),
                    })
            except Exception as e:
                print(f"[TTS] Error: {e}")
            await websocket.send_json({"type": "audio_end"})

            # Step 6: Follow-up prompt for missing fields
            if result.missing_fields:
                follow_up_text = _build_follow_up_text(result.missing_fields, result.follow_up_questions)
                await websocket.send_json({
                    "type": "follow_up",
                    "missing_fields": result.missing_fields,
                    "prompt": follow_up_text,
                })
                try:
                    fu_audio = await tts.synthesize(follow_up_text)
                    if fu_audio:
                        await websocket.send_json({
                            "type": "audio",
                            "data": base64.b64encode(fu_audio).decode(),
                        })
                except Exception as e:
                    print(f"[TTS] Follow-up TTS error: {e}")
                await websocket.send_json({"type": "audio_end"})

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected. officer_id={officer_id}")
    except Exception as e:
        print(f"[WS] Unexpected error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
