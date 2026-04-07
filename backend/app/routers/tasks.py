"""
CRUD endpoints for patrol tasks.
In a full deployment these would read/write to Supabase.
For now, an in-memory store is used as a working placeholder.
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import Task, TaskCreate
from datetime import datetime
import uuid

router = APIRouter(prefix="/tasks", tags=["tasks"])

# In-memory task store — replace with Supabase client calls
_tasks: dict[str, Task] = {}


@router.get("", response_model=list[Task])
async def list_tasks():
    return sorted(_tasks.values(), key=lambda t: t.created_at, reverse=True)


@router.post("", response_model=Task, status_code=201)
async def create_task(data: TaskCreate):
    task = Task(
        id=str(uuid.uuid4()),
        officer_id=data.officer_id,
        priority=data.priority,
        category=data.category,
        action=data.action,
        summary=data.summary,
        created_at=datetime.utcnow(),
    )
    _tasks[task.id] = task
    return task


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found.")
    del _tasks[task_id]
