"""
Real-Time Intelligence Engine
Queries mock datasets to surface relevant info during an active incident.
"""
import json
import os
from typing import Optional

# --- Load datasets once at startup ---

def load_json(filename: str) -> list:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "data", filename)
    with open(path, "r") as f:
        return json.load(f)

try:
    CASES = load_json("mock_cases.json")
    OFFENDERS = load_json("mock_offenders.json")
    CAMERAS = load_json("mock_cctv_locations.json")
    print(f"[Intelligence] Loaded {len(CASES)} cases, {len(OFFENDERS)} offenders, {len(CAMERAS)} cameras.")
except Exception as e:
    print(f"[Intelligence] Warning — could not load datasets: {e}")
    CASES, OFFENDERS, CAMERAS = [], [], []


# --- Query functions ---

def get_cases_by_location(location: str, limit: int = 5) -> list:
    """
    Return past cases at or near a given location.
    Simple string match — good enough for demo.
    """
    location_lower = location.lower()
    matches = [
        c for c in CASES
        if location_lower in c["location"].lower()
    ]
    # sort by most recent first
    matches.sort(key=lambda c: c["created_at"], reverse=True)
    return matches[:limit]


def get_offenders_by_description(
    gender: Optional[str] = None,
    build: Optional[str] = None,
    clothing: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 5
) -> list:
    scored = []

    for offender in OFFENDERS:
        score = 0
        desc = offender.get("description", {})

        # gender is a hard filter — skip if it doesn't match
        if gender and offender.get("gender", "").lower() != gender.lower():
            continue

        if build and desc.get("build", "").lower() == build.lower():
            score += 2

        if clothing and clothing.lower() in desc.get("last_seen_wearing", "").lower():
            score += 3

        if location and location.lower() in offender.get("last_known_location", "").lower():
            score += 1

        # only include if at least one optional field matched
        if score > 0:
            scored.append({**offender, "match_score": score})

    risk_order = {"high": 3, "medium": 2, "low": 1}
    scored.sort(
        key=lambda o: (o["match_score"], risk_order.get(o["risk_level"], 0)),
        reverse=True
    )
    return scored[:limit]


def get_offenders_by_location(location: str, limit: int = 3) -> list:
    """Return offenders last seen at or near a location."""
    location_lower = location.lower()
    matches = [
        o for o in OFFENDERS
        if location_lower in o.get("last_known_location", "").lower()
    ]
    # prioritise high risk and outstanding warrants
    matches.sort(
        key=lambda o: (
            o.get("outstanding_warrant", False),
            {"high": 3, "medium": 2, "low": 1}.get(o["risk_level"], 0)
        ),
        reverse=True
    )
    return matches[:limit]


def get_cameras_near_location(location: str, limit: int = 3) -> list:
    """Return online CCTV cameras near a given location name."""
    location_lower = location.lower()
    matches = [
        c for c in CAMERAS
        if location_lower in c["location_name"].lower()
        and c["status"] == "online"
    ]
    return matches[:limit]


def get_high_risk_offenders(limit: int = 5) -> list:
    """Return all high-risk offenders with outstanding warrants."""
    matches = [
        o for o in OFFENDERS
        if o["risk_level"] == "high" or o.get("outstanding_warrant", False)
    ]
    matches.sort(
        key=lambda o: (
            o.get("outstanding_warrant", False),
            o["risk_level"] == "high"
        ),
        reverse=True
    )
    return matches[:limit]


def run_full_intelligence_check(
    location: str,
    gender: Optional[str] = None,
    build: Optional[str] = None,
    clothing: Optional[str] = None,
) -> dict:
    """
    Run all intelligence queries for an active incident.
    Returns a combined result dict ready to send via WebSocket.
    """
    past_cases = get_cases_by_location(location)
    suspect_matches = get_offenders_by_description(gender, build, clothing, location)
    area_offenders = get_offenders_by_location(location)
    nearby_cameras = get_cameras_near_location(location)

    # determine overall threat level
    has_warrant = any(o.get("outstanding_warrant") for o in suspect_matches)
    has_high_risk = any(o["risk_level"] == "high" for o in suspect_matches)
    threat_level = "high" if has_warrant or has_high_risk else (
        "medium" if suspect_matches else "low"
    )

    return {
        "event": "intelligence.result",
        "location": location,
        "threat_level": threat_level,
        "past_cases": past_cases,
        "suspect_matches": suspect_matches,
        "area_offenders": area_offenders,
        "nearby_cameras": nearby_cameras,
        "summary": build_summary(location, past_cases, suspect_matches, threat_level)
    }


def build_summary(location, past_cases, suspect_matches, threat_level) -> str:
    """Build a plain English summary for the officer."""
    parts = []

    if past_cases:
        parts.append(f"{len(past_cases)} past incident(s) recorded at {location}")

    if suspect_matches:
        top = suspect_matches[0]
        warrant = " — OUTSTANDING WARRANT" if top.get("outstanding_warrant") else ""
        parts.append(
            f"Closest suspect match: {top['name']}, {top['age']}yo {top['gender']}, "
            f"risk level {top['risk_level'].upper()}{warrant}"
        )

    if not parts:
        parts.append(f"No prior incidents or known offenders recorded at {location}")

    return ". ".join(parts) + "."