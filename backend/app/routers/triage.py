"""
REST endpoint for triaging a text transcript directly (no audio).
POST /triage { "transcript": "...", "officer_id": "..." }
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import TriageRequest, Task
from app.services import llm, cache
from app.services.db import get_supabase
from app.websocket.manager import manager
from app.websocket.events import Events
import uuid
from datetime import datetime


def _valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(val)
        return True
    except (ValueError, AttributeError):
        return False

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("", response_model=Task)
async def triage_text(req: TriageRequest):
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty.")

    # Check cache first
    result = await cache.get_cached(req.transcript)

    if result is None:
        try:
            result = await llm.triage_transcript(req.transcript)
            await cache.set_cached(req.transcript, result)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"LLM triage failed: {e}")

    escalated_at = datetime.utcnow() if result.escalation_required else None
    officer_id = req.officer_id if req.officer_id and _valid_uuid(req.officer_id) else None

    task = Task(
        id=str(uuid.uuid4()),
        officer_id=officer_id,
        priority=result.priority,
        category=result.category,
        action=result.action,
        summary=result.summary,
        created_at=datetime.utcnow(),
        escalation_required=result.escalation_required,
        escalation_reason=result.escalation_reason,
        severity_flags=result.severity_flags,
        requires_supervisor=result.requires_supervisor,
        escalated_at=escalated_at,
    )

    # Persist to Supabase
    sb = get_supabase()
    res = sb.table("tasks").insert(task.model_dump(by_alias=True, mode="json", exclude_none=True)).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to persist task.")
    task = Task.model_validate(res.data[0])

    now = datetime.utcnow().isoformat()

    if result.escalation_required:
        await manager.broadcast({
            "event": Events.ESCALATION_TRIGGERED,
            "task_id": task.id,
            "officer_id": req.officer_id,
            "escalation_reason": result.escalation_reason,
            "severity_flags": result.severity_flags,
            "requires_supervisor": result.requires_supervisor,
            "summary": result.summary,
            "timestamp": now,
        })

    if result.requires_supervisor:
        await manager.broadcast({
            "event": Events.SUPERVISOR_NOTIFIED,
            "task_id": task.id,
            "officer_id": req.officer_id,
            "reason": result.escalation_reason,
            "timestamp": now,
        })

    return task
