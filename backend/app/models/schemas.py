from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime
import uuid


class TriageResult(BaseModel):
    priority: Literal["high", "medium", "low"]
    action: str = Field(description="Specific action the officer should take")
    category: Literal["patrol", "incident", "admin"]
    summary: str = Field(description="Brief summary of the officer's report")


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    officer_id: Optional[str] = None
    priority: Literal["high", "medium", "low"]
    category: Literal["patrol", "incident", "admin"]
    action: str
    summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TriageRequest(BaseModel):
    transcript: str
    officer_id: Optional[str] = None


class TaskCreate(BaseModel):
    officer_id: Optional[str] = None
    priority: Literal["high", "medium", "low"] = "low"
    category: Literal["patrol", "incident", "admin"] = "patrol"
    action: str
    summary: str


class OfficerCreate(BaseModel):
    name: str
    badge_number: str
    status: str = "active"
