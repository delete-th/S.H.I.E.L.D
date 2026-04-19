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

_RESET_PHRASES = {"new case", "new incident", "next report", "new report", "fresh case", "start over"}


def _build_follow_up_text(missing_fields: list) -> str:
    return " ".join(
        FOLLOW_UP_PROMPTS[f] for f in missing_fields if f in FOLLOW_UP_PROMPTS
    )


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

    try:
        while True:
            audio_bytes = await websocket.receive_bytes()
            if not audio_bytes:
                continue

            # Step 1: Transcribe
            try:
                transcript = await stt.transcribe(audio_bytes)
            except Exception as e:
                await websocket.send_json({"type": "error", "message": f"STT failed: {e}"})
                continue

            if not transcript:
                await websocket.send_json({"type": "error", "message": "No speech detected."})
                continue

            await websocket.send_json({"type": "transcript", "text": transcript})

            # Reset conversation if officer signals a new case
            if _is_reset_phrase(transcript):
                conversation_history.clear()
                await websocket.send_json({"type": "conversation_reset"})

            # Step 2: Cache check + LLM triage (with conversation history)
            result = await cache.get_cached(transcript)
            if result is None:
                try:
                    result = await llm.triage_transcript(transcript, history=conversation_history)
                    await cache.set_cached(transcript, result)
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"LLM failed: {e}"})
                    continue

            # Append to conversation history (cap at 10 messages / 5 turns)
            conversation_history.append({"role": "user", "content": f"Officer report: {transcript}"})
            conversation_history.append({"role": "assistant", "content": result.model_dump_json()})
            if len(conversation_history) > 10:
                conversation_history = conversation_history[-10:]

            tts_text = tts.build_tts_text(result)
            await websocket.send_json({"type": "triage", "result": result.model_dump(), "tts_text": tts_text})

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
                follow_up_text = _build_follow_up_text(result.missing_fields)
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
