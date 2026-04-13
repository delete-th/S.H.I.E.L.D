"""
CRUD endpoints for patrol tasks — backed by Supabase.
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import Task, TaskCreate
from app.services.db import get_supabase

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
async def list_tasks():
    sb = get_supabase()
    res = sb.table("tasks").select("*").order("t_created_at", desc=True).execute()
    return [Task.model_validate(row) for row in res.data]


@router.post("", response_model=Task, status_code=201)
async def create_task(data: TaskCreate):
    sb = get_supabase()
    task = Task(
        officer_id=data.officer_id,
        priority=data.priority,
        category=data.category,
        action=data.action,
        summary=data.summary,
    )
    res = sb.table("tasks").insert(task.model_dump(by_alias=True, mode="json", exclude_none=True)).execute()
    return Task.model_validate(res.data[0])


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str):
    sb = get_supabase()
    res = sb.table("tasks").select("*").eq("t_id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found.")
    return Task.model_validate(res.data[0])


@router.patch("/{task_id}", response_model=Task)
async def update_task(task_id: str, resolved: bool):
    sb = get_supabase()
    res = sb.table("tasks").update({"t_resolved": resolved}).eq("t_id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found.")
    return Task.model_validate(res.data[0])


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str):
    sb = get_supabase()
    res = sb.table("tasks").select("t_id").eq("t_id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found.")
    sb.table("tasks").delete().eq("t_id", task_id).execute()
