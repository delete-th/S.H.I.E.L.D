"""
Missing Person endpoints:
  POST /missing-person/search          — search by uploaded photo
  POST /missing-person/watchlist       — add a face to the watchlist
  GET  /missing-person/watchlist       — list all watchlist entries
  DELETE /missing-person/watchlist/{id} — remove from watchlist
  GET  /missing-person/status/{id}     — search status
"""
import asyncio
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.face_search import (
    extract_embedding_from_bytes,
    scan_cctv_for_person,
    load_known_faces,
    register_face,
    list_watchlist,
    remove_from_watchlist,
)
from app.services.cctv import cctv_manager, CCTVHandler
from app.websocket.manager import manager
from app.websocket.events import Events
import os

router = APIRouter(prefix="/missing-person", tags=["missing-person"])

# In-memory state
known_faces: dict    = {}
active_searches: dict = {}


@router.on_event("startup")
async def _load_faces():
    global known_faces
    known_faces = load_known_faces()
    print(f"[MissingPerson] {len(known_faces)} faces in watchlist.")


# ── Watchlist management ──────────────────────────────────────────────────────

@router.post("/watchlist")
async def add_to_watchlist(
    name: str = Form(...),
    notes: str = Form(""),
    photo: UploadFile = File(...),
):
    """Add a face photo to the searchable watchlist."""
    data = await photo.read()
    if not data:
        raise HTTPException(400, "Empty photo.")

    # Validate face is detectable
    emb = extract_embedding_from_bytes(data)
    if emb is None:
        raise HTTPException(422, "No face detected in photo. Please upload a clear front-facing photo.")

    record = register_face(data, name, notes)

    # Reload cache so future searches include this face
    global known_faces
    known_faces = load_known_faces()

    return {"status": "registered", "record": record, "watchlist_size": len(known_faces)}


@router.get("/watchlist")
async def get_watchlist():
    return {"entries": list_watchlist(), "total": len(known_faces)}


@router.delete("/watchlist/{face_id}")
async def delete_from_watchlist(face_id: str):
    removed = remove_from_watchlist(face_id)
    if not removed:
        raise HTTPException(404, "Face ID not found.")
    global known_faces
    known_faces = load_known_faces()
    return {"status": "removed", "face_id": face_id}


# ── Search ────────────────────────────────────────────────────────────────────

@router.post("/search")
async def start_search(
    officer_id:  str = Form(...),
    description: str = Form(""),
    photo: UploadFile = File(...),
):
    """Officer uploads photo → scan watchlist + all CCTV feeds."""
    photo_bytes = await photo.read()
    if not photo_bytes:
        raise HTTPException(400, "Empty photo.")

    target_embedding = extract_embedding_from_bytes(photo_bytes)
    if target_embedding is None:
        raise HTTPException(422, "No face detected in photo. Upload a clear front-facing photo.")

    search_id = str(uuid.uuid4())[:8]
    active_searches[search_id] = {
        "status": "scanning",
        "officer_id": officer_id,
        "description": description,
        "result": None,
        "cameras_scanned": [],
    }

    cameras = cctv_manager.list_cameras()

    await manager.send_to_officer(officer_id, {
        "event": Events.MISSING_PERSON_SEARCH_STARTED,
        "search_id": search_id,
        "message": f"Scanning watchlist ({len(known_faces)} faces) + {len(cameras)} camera(s)...",
    })

    base_dir   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    video_path = os.path.join(base_dir, "data", "mock_cctv.mp4")

    for camera_id in cameras:
        handler = CCTVHandler(
            source="file",
            camera_id=camera_id,
            file_path=video_path,
            frame_interval=0.3,
            max_frames=60,
        )

        async def on_match(result, sid=search_id, oid=officer_id, cid=camera_id):
            active_searches[sid]["status"] = "found"
            active_searches[sid]["result"] = result
            active_searches[sid]["cameras_scanned"].append(cid)

            source_label = (
                f"watchlist database ({result.get('name', 'Unknown')})"
                if result.get("source") == "watchlist"
                else f"CCTV {cid}"
            )

            await manager.send_to_officer(oid, {
                "event": Events.MISSING_PERSON_FOUND,
                "search_id": sid,
                "camera_id": cid,
                "name": result.get("name", "Unknown"),
                "confidence": result["confidence"],
                "timestamp": result["timestamp"],
                "source": result.get("source"),
                "message": f"Person located on {source_label} — {result['confidence']}% confidence.",
            })

        asyncio.create_task(scan_cctv_for_person(
            target_embedding=target_embedding,
            known_faces=known_faces,
            camera_id=camera_id,
            cctv_handler=handler,
            on_match=on_match,
            max_frames=60,
        ))

    return {
        "search_id": search_id,
        "status": "scanning",
        "watchlist_size": len(known_faces),
        "cameras": cameras,
    }


@router.get("/status/{search_id}")
async def get_status(search_id: str):
    s = active_searches.get(search_id)
    if not s:
        raise HTTPException(404, "Search not found.")
    return s


@router.get("/status")
async def list_searches():
    return {"searches": active_searches, "total": len(active_searches)}