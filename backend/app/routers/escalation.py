"""
Safety & Escalation Layer — Feature 7.

Endpoints:
  POST /escalation/trigger  — manually escalate an existing task
  GET  /escalation/active   — list all unresolved escalated tasks
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.schemas import Task
from app.services.db import get_supabase
from app.websocket.manager import manager
from app.websocket.events import Events

router = APIRouter(prefix="/escalation", tags=["escalation"])


class EscalationTrigger(BaseModel):
    task_id: str
    officer_id: Optional[str] = None
    reason: str
    severity_flags: List[str] = []
    requires_supervisor: bool = False


@router.post("/trigger", response_model=Task)
async def trigger_escalation(body: EscalationTrigger):
    sb = get_supabase()

    # Verify task exists
    check = sb.table("tasks").select("t_id").eq("t_id", body.task_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Task not found.")

    escalated_at = datetime.utcnow().isoformat()

    res = sb.table("tasks").update({
        "t_escalation_required": True,
        "t_escalation_reason": body.reason,
        "t_severity_flags": body.severity_flags,
        "t_requires_supervisor": body.requires_supervisor,
        "t_escalated_at": escalated_at,
    }).eq("t_id", body.task_id).execute()

    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to update task.")

    await manager.broadcast({
        "event": Events.ESCALATION_TRIGGERED,
        "task_id": body.task_id,
        "officer_id": body.officer_id,
        "escalation_reason": body.reason,
        "severity_flags": body.severity_flags,
        "requires_supervisor": body.requires_supervisor,
        "timestamp": escalated_at,
    })

    return Task.model_validate(res.data[0])


@router.get("/active", response_model=List[Task])
async def list_active_escalations():
    sb = get_supabase()
    res = (
        sb.table("tasks")
        .select("*")
        .eq("t_escalation_required", True)
        .eq("t_resolved", False)
        .order("t_escalated_at", desc=True)
        .execute()
    )
    return [Task.model_validate(row) for row in res.data]
