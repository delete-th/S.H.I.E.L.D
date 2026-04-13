"""
Routing service using OneMap API (Singapore's official mapping API).
Free, no billing required — just needs an API key.

Used for:
- Getting route between two points (officer → interception point)
- Predicting suspect escape routes
- Finding nearest officers to a location
"""
import httpx
from geopy.distance import geodesic
from typing import Optional
from app.config import settings


# --- OneMap token management ---

token: str = ""


async def get_token() -> str:
    """
    Get a valid OneMap API token.
    Tokens expire after 3 days - for demo, we fetch fresh each time.
    """
    global token
    if token:
        return token

    if not settings.onemap_api_key:
        print("[Routing] No OneMap API key set - using mock routing.")
        return ""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.onemap_base_url}/api/auth/post/getToken",
            json={"email": "", "password": settings.onemap_api_key}
        )
        data = response.json()
        token = data.get("access_token", "")
        return token


async def get_route(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    route_type: str = "walk"  # "walk" | "drive" | "pt"
) -> dict:
    """
    Get a route between two coordinates using OneMap.
    Returns route geometry, distance, and estimated time.
    """
    token = await get_token()

    # fall back to mock route if no API key
    if not token:
        return mock_route(start_lat, start_lng, end_lat, end_lng)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{settings.onemap_base_url}/api/public/routingsvc/route",
            params={
                "start": f"{start_lat},{start_lng}",
                "end": f"{end_lat},{end_lng}",
                "routeType": route_type,
                "token": token,
            }
        )
        response.raise_for_status()
        data = response.json()

    # extract key info from OneMap response
    route_summary = data.get("route_summary", {})
    route_geometry = data.get("route_geometry", "")

    return {
        "start": {"lat": start_lat, "lng": start_lng},
        "end": {"lat": end_lat, "lng": end_lng},
        "distance_m": route_summary.get("total_distance", 0),
        "duration_s": route_summary.get("total_time", 0),
        "geometry": route_geometry,  # encoded polyline for frontend map
        "route_type": route_type,
    }


def find_nearest_officers(
    suspect_location: dict,
    officer_locations: dict,
    limit: int = 3
) -> list:
    """
    Find the closest officers to a suspect location.

    suspect_location: { lat, lng }
    officer_locations: { officer_id: { lat, lng } }

    Returns list of officers sorted by distance.
    """
    suspect_point = (suspect_location["lat"], suspect_location["lng"])
    distances = []

    for officer_id, loc in officer_locations.items():
        officer_point = (loc["lat"], loc["lng"])
        distance_km = geodesic(suspect_point, officer_point).km
        distances.append({
            "officer_id": officer_id,
            "lat": loc["lat"],
            "lng": loc["lng"],
            "distance_km": round(distance_km, 3),
            "distance_m": round(distance_km * 1000)
        })

    distances.sort(key=lambda x: x["distance_km"])
    return distances[:limit]


def predict_escape_routes(
    suspect_lat: float,
    suspect_lng: float
) -> list:
    """
    Predict likely escape routes based on suspect's current position.
    Uses cardinal directions + estimated movement to generate 
    interception points ahead of the suspect.

    In production this would use real street graph data.
    For demo, generates realistic directional predictions.
    """
    import math

    # predict positions 200m, 400m, 600m ahead in 4 directions
    escape_routes = []
    directions = {
        "north": 0,
        "east": 90,
        "south": 180,
        "west": 270
    }

    for direction, bearing in directions.items():
        points = []
        for distance_m in [200, 400, 600]:
            # convert bearing + distance to lat/lng offset
            lat, lng = offset_coordinate(
                suspect_lat, suspect_lng,
                bearing, distance_m
            )
            points.append({"lat": lat, "lng": lng, "distance_m": distance_m})

        escape_routes.append({
            "direction": direction,
            "bearing": bearing,
            "interception_points": points
        })

    return escape_routes


def offset_coordinate(
    lat: float,
    lng: float,
    bearing_deg: float,
    distance_m: float
) -> tuple:
    """
    Calculate a new lat/lng given a starting point, bearing, and distance.
    Uses simple flat-earth approximation. accurate enough for <1km.
    """
    import math

    R = 6371000  # Earth radius in metres
    bearing_rad = math.radians(bearing_deg)

    lat_rad = math.radians(lat)
    lng_rad = math.radians(lng)

    new_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(distance_m / R) +
        math.cos(lat_rad) * math.sin(distance_m / R) * math.cos(bearing_rad)
    )

    new_lng_rad = lng_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(distance_m / R) * math.cos(lat_rad),
        math.cos(distance_m / R) - math.sin(lat_rad) * math.sin(new_lat_rad)
    )

    return round(math.degrees(new_lat_rad), 6), round(math.degrees(new_lng_rad), 6)


def mock_route(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float
) -> dict:
    """Fallback mock route when no API key is set."""
    distance_m = geodesic(
        (start_lat, start_lng),
        (end_lat, end_lng)
    ).meters

    return {
        "start": {"lat": start_lat, "lng": start_lng},
        "end": {"lat": end_lat, "lng": end_lng},
        "distance_m": round(distance_m),
        "duration_s": round(distance_m / 1.4),  # avg walking speed 1.4m/s
        "geometry": "",
        "route_type": "walk",
        "mock": True
    }