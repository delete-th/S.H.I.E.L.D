"""
Intelligence endpoints:
  POST /intelligence/check     - run full intelligence check for an incident
  GET  /intelligence/offenders - list high-risk offenders
  GET  /intelligence/cases     - get past cases by location
"""
from fastapi import APIRouter, Query
from app.services.intelligence import (
    run_full_intelligence_check,
    get_high_risk_offenders,
    get_cases_by_location,
    get_offenders_by_description
)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.post("/check")
async def intelligence_check(body: dict):
    """
    Run a full intelligence check for an active incident.

    Body:
    {
        "location": "Tampines Mall",
        "gender": "Male",           (optional)
        "build": "slim",            (optional)
        "clothing": "black hoodie"  (optional)
    }
    """
    result = run_full_intelligence_check(
        location=body.get("location", ""),
        gender=body.get("gender"),
        build=body.get("build"),
        clothing=body.get("clothing"),
    )
    return result


@router.get("/offenders")
async def list_high_risk_offenders():
    """Return all high-risk offenders and those with outstanding warrants."""
    return {
        "offenders": get_high_risk_offenders(),
        "total": len(get_high_risk_offenders())
    }


@router.get("/cases")
async def list_cases_by_location(
    location: str = Query(..., description="Location name to search")
):
    """Return past cases at a given location."""
    cases = get_cases_by_location(location)
    return {
        "location": location,
        "cases": cases,
        "total": len(cases)
    }


@router.get("/suspects")
async def search_suspects(
    gender: str = Query(None),
    build: str = Query(None),
    clothing: str = Query(None),
    location: str = Query(None)
):
    """Search for known offenders matching a physical description."""
    matches = get_offenders_by_description(gender, build, clothing, location)
    return {
        "matches": matches,
        "total": len(matches)
    }