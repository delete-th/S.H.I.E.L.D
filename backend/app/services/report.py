"""
Report generation service — orchestrates LLM report generation and Supabase persistence.
"""
import uuid
from datetime import datetime
from app.models.schemas import IncidentReport
from app.services import llm
from app.services.db import get_supabase


def _generate_report_number() -> str:
    date_str = datetime.utcnow().strftime("%Y%m%d")
    suffix = str(uuid.uuid4()).replace("-", "")[:4].upper()
    return f"RPT-{date_str}-{suffix}"


async def create_report_from_task(task_id: str, officer_id: str | None) -> IncidentReport:
    """
    Fetch task from Supabase, run LLM report generation, persist and return the report.
    Raises ValueError if task_id not found.
    """
    sb = get_supabase()

    task_res = sb.table("tasks").select("*").eq("t_id", task_id).execute()
    if not task_res.data:
        raise ValueError(f"Task {task_id} not found")

    task_row = task_res.data[0]
    summary = task_row.get("t_summary", "")
    action = task_row.get("t_action", "")
    severity_flags = task_row.get("t_severity_flags") or []

    report_data = await llm.generate_report(summary, action, severity_flags)

    report_id = str(uuid.uuid4())
    now = datetime.utcnow()

    report = IncidentReport(
        r_id=report_id,
        r_report_number=_generate_report_number(),
        r_task_id=task_id,
        r_officer_id=officer_id,
        r_incident_type=report_data.get("incident_type", "Unknown"),
        r_location=report_data.get("location"),
        r_date_time=now,
        r_description=report_data.get("description", ""),
        r_actions_taken=report_data.get("actions_taken", ""),
        r_persons_involved=report_data.get("persons_involved", []),
        r_evidence=report_data.get("evidence", []),
        r_follow_up_required=bool(report_data.get("follow_up_required", False)),
        r_status="draft",
        r_created_at=now,
    )

    sb.table("reports").insert(
        report.model_dump(by_alias=True, mode="json", exclude_none=True)
    ).execute()

    return report
