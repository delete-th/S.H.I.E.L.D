from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional, List
from datetime import datetime
import uuid


class TriageResult(BaseModel):
    priority: Literal["high", "medium", "low"]
    action: str = Field(description="Specific action the officer should take")
    category: Literal["patrol", "incident", "admin"]
    summary: str = Field(description="Brief summary of the officer's report")
    escalation_required: bool = False
    escalation_reason: Optional[str] = None
    severity_flags: List[str] = []
    requires_supervisor: bool = False
    missing_fields: List[str] = []


class IncidentReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="r_id")
    report_number: str = Field(alias="r_report_number")
    task_id: Optional[str] = Field(default=None, alias="r_task_id")
    officer_id: Optional[str] = Field(default=None, alias="r_officer_id")
    incident_type: str = Field(alias="r_incident_type")
    location: Optional[str] = Field(default=None, alias="r_location")
    date_time: datetime = Field(alias="r_date_time")
    description: str = Field(alias="r_description")
    actions_taken: str = Field(alias="r_actions_taken")
    persons_involved: List[str] = Field(default_factory=list, alias="r_persons_involved")
    evidence: List[str] = Field(default_factory=list, alias="r_evidence")
    follow_up_required: bool = Field(default=False, alias="r_follow_up_required")
    status: Literal["draft", "submitted", "approved"] = Field(default="draft", alias="r_status")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="r_created_at")


class Task(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="t_id")
    officer_id: Optional[str] = Field(default=None, alias="t_officer_id")
    priority: Literal["high", "medium", "low"] = Field(alias="t_priority")
    category: Literal["patrol", "incident", "admin"] = Field(alias="t_category")
    action: str = Field(alias="t_action")
    summary: str = Field(alias="t_summary")
    resolved: bool = Field(default=False, alias="t_resolved")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="t_created_at")
    escalation_required: bool = Field(default=False, alias="t_escalation_required")
    escalation_reason: Optional[str] = Field(default=None, alias="t_escalation_reason")
    severity_flags: List[str] = Field(default_factory=list, alias="t_severity_flags")
    requires_supervisor: bool = Field(default=False, alias="t_requires_supervisor")
    escalated_at: Optional[datetime] = Field(default=None, alias="t_escalated_at")


class TriageRequest(BaseModel):
    transcript: str
    officer_id: Optional[str] = None


class TaskCreate(BaseModel):
    officer_id: Optional[str] = None
    priority: Literal["high", "medium", "low"] = "low"
    category: Literal["patrol", "incident", "admin"] = "patrol"
    action: str
    summary: str
    escalation_required: bool = False
    escalation_reason: Optional[str] = None
    severity_flags: List[str] = []
    requires_supervisor: bool = False


class OfficerCreate(BaseModel):
    name: str
    badge_number: str
    status: str = "active"
