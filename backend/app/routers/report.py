"""
Incident Report endpoints:
  POST /report/generate    — generate report from existing task_id
  GET  /report             — list all reports newest-first
  GET  /report/{report_id} — retrieve a single report
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.models.schemas import IncidentReport
from app.services.report import create_report_from_task
from app.services.db import get_supabase

router = APIRouter(prefix="/report", tags=["report"])


class GenerateReportRequest(BaseModel):
    task_id: str
    officer_id: Optional[str] = None


@router.post("/generate", response_model=IncidentReport, status_code=201)
async def generate_report(req: GenerateReportRequest):
    try:
        return await create_report_from_task(req.task_id, req.officer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Report generation failed: {e}")


@router.get("", response_model=List[IncidentReport])
async def list_reports():
    sb = get_supabase()
    res = sb.table("reports").select("*").order("r_created_at", desc=True).execute()
    return [IncidentReport.model_validate(row) for row in res.data]


@router.get("/{report_id}", response_model=IncidentReport)
async def get_report(report_id: str):
    sb = get_supabase()
    res = sb.table("reports").select("*").eq("r_id", report_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Report not found.")
    return IncidentReport.model_validate(res.data[0])
