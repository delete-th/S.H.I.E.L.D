from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import manager
from app.websocket.events import Events

router = APIRouter()

# In-memory officer location store - replace with Redis in production
officer_locations: dict = {}

@router.websocket("/ws/coordination/{officer_id}")
async def coordination_websocket(websocket: WebSocket, officer_id: str):
    await manager.connect(officer_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            # Officer sends GPS update
            if event == Events.OFFICER_LOCATION:
                officer_locations[officer_id] = {
                    "lat": data["lat"],
                    "lng": data["lng"]
                }
                # broadcast to all so dashboard map updates
                await manager.broadcast({
                    "event": Events.OFFICER_LOCATION,
                    "officer_id": officer_id,
                    "lat": data["lat"],
                    "lng": data["lng"]
                })

            # Officer reports a suspect sighting
            elif event == Events.SUSPECT_LOCATED:
                suspect_loc = {"lat": data["lat"], "lng": data["lng"]}
                # alert nearby officers within 1km
                await manager.broadcast_to_nearby(
                    message={
                        "event": Events.SUSPECT_LOCATED,
                        "reported_by": officer_id,
                        "description": data.get("description", ""),
                        "lat": data["lat"],
                        "lng": data["lng"]
                    },
                    officer_locations=officer_locations,
                    origin=suspect_loc,
                    radius_km=1.0
                )

            # Assign chaser/interceptor role to another officer
            elif event == Events.ROLE_ASSIGNED:
                target = data.get("target_officer_id")
                role = data.get("role")
                if role not in ("chaser", "interceptor") or not target:
                    continue
                payload = {
                    "event": Events.ROLE_ASSIGNED,
                    "target_officer_id": target,
                    "assigned_by": officer_id,
                    "role": role,
                    "suspect_description": data.get("suspect_description", ""),
                    "location": data.get("location", {}),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                await manager.send_to_officer(target, payload)
                await manager.broadcast(payload)

    except WebSocketDisconnect:
        manager.disconnect(officer_id)
        await manager.broadcast({
            "event": Events.OFFICER_OFFLINE,
            "officer_id": officer_id
        })