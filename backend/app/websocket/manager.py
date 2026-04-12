from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        # active officer connections keyed by officer_id
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, officer_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[officer_id] = websocket
        print(f"[WS] Officer {officer_id} connected. Total: {len(self.active_connections)}")

        # notify all others that this officer is online
        await self.broadcast({
            "event": "officer.online",
            "officer_id": officer_id
        }, exclude=officer_id)

    def disconnect(self, officer_id: str):
        self.active_connections.pop(officer_id, None)
        print(f"[WS] Officer {officer_id} disconnected.")

    async def send_to_officer(self, officer_id: str, message: dict):
        """Send message to one specific officer"""
        ws = self.active_connections.get(officer_id)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, message: dict, exclude: str = None):
        """Send message to all connected officers, optionally excluding one"""
        for oid, ws in self.active_connections.items():
            if oid != exclude:
                await ws.send_json(message)

    async def broadcast_to_nearby(
        self,
        message: dict,
        officer_locations: Dict[str, dict],
        origin: dict,
        radius_km: float = 1.0
    ):
        """
        Broadcast only to officers within radius_km of a location.
        officer_locations: { officer_id: { lat, lng } }
        origin: { lat, lng }
        """
        from geopy.distance import geodesic
        origin_point = (origin["lat"], origin["lng"])

        for oid, loc in officer_locations.items():
            point = (loc["lat"], loc["lng"])
            distance = geodesic(origin_point, point).km
            if distance <= radius_km:
                await self.send_to_officer(oid, message)

    def get_online_officers(self) -> List[str]:
        return list(self.active_connections.keys())


# single shared instance — imported wherever needed
manager = ConnectionManager()