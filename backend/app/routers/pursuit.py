"""
Pursuit & Interception endpoints:
  POST /pursuit/start          — start tracking a fleeing suspect
  POST /pursuit/interception   — calculate interception points
  GET  /pursuit/route          — get route between two coordinates
"""
from fastapi import APIRouter
from app.services.routing import (
    get_route,
    find_nearest_officers,
    predict_escape_routes
)
from app.websocket.manager import manager
from app.websocket.events import Events
from app.routers.coordination import officer_locations

router = APIRouter(prefix="/pursuit", tags=["pursuit"])


@router.post("/start")
async def start_pursuit(body: dict):
    """
    Officer reports a fleeing suspect.
    System calculates escape routes and alerts nearby officers.

    Body:
    {
        "officer_id": "C-001",
        "suspect_lat": 1.3521,
        "suspect_lng": 103.8198,
        "description": "Male, black hoodie, heading north"
    }
    """
    suspect_lat = body["suspect_lat"]
    suspect_lng = body["suspect_lng"]
    officer_id = body.get("officer_id", "unknown")
    description = body.get("description", "No description provided")

    # predict escape routes
    escape_routes = predict_escape_routes(suspect_lat, suspect_lng)

    # find nearest officers
    nearest = find_nearest_officers(
        suspect_location={"lat": suspect_lat, "lng": suspect_lng},
        officer_locations=officer_locations
    )

    # broadcast suspect location to all officers
    await manager.broadcast({
        "event": Events.SUSPECT_LOCATED,
        "reported_by": officer_id,
        "description": description,
        "lat": suspect_lat,
        "lng": suspect_lng,
        "escape_routes": escape_routes,
        "nearest_officers": nearest
    })

    return {
        "status": "pursuit_started",
        "suspect_location": {"lat": suspect_lat, "lng": suspect_lng},
        "description": description,
        "escape_routes": escape_routes,
        "nearest_officers": nearest,
        "officers_alerted": len(officer_locations)
    }


@router.post("/interception")
async def calculate_interception(body: dict):
    """
    Calculate the best interception point and route for an officer.

    Body:
    {
        "officer_lat": 1.3500,
        "officer_lng": 103.8200,
        "suspect_lat": 1.3521,
        "suspect_lng": 103.8198,
        "route_type": "walk"
    }
    """
    officer_lat = body["officer_lat"]
    officer_lng = body["officer_lng"]
    suspect_lat = body["suspect_lat"]
    suspect_lng = body["suspect_lng"]
    route_type = body.get("route_type", "walk")

    # get route from officer to suspect
    route = await get_route(
        officer_lat, officer_lng,
        suspect_lat, suspect_lng,
        route_type
    )

    # predict where suspect will be and suggest interception ahead
    escape_routes = predict_escape_routes(suspect_lat, suspect_lng)

    # pick the closest interception point from the first escape route
    best_interception = None
    if escape_routes:
        north_route = escape_routes[0]["interception_points"]
        best_interception = north_route[0]  # 200m ahead

    return {
        "route_to_suspect": route,
        "best_interception_point": best_interception,
        "all_escape_routes": escape_routes,
        "eta_seconds": route["duration_s"],
        "distance_m": route["distance_m"]
    }


@router.get("/route")
async def get_directions(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    route_type: str = "walk"
):
    """Get walking/driving route between two coordinates."""
    route = await get_route(start_lat, start_lng, end_lat, end_lng, route_type)
    return route