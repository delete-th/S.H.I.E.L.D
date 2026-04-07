"""
REST endpoint for triaging a text transcript directly (no audio).
POST /triage { "transcript": "...", "officer_id": "..." }
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import TriageRequest, Task
from app.services import llm, cache
import uuid
from datetime import datetime

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

    return Task(
        id=str(uuid.uuid4()),
        officer_id=req.officer_id,
        priority=result.priority,
        category=result.category,
        action=result.action,
        summary=result.summary,
        created_at=datetime.utcnow(),
    )
