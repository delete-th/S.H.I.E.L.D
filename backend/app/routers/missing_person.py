import asyncio
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.face_search import (
    extract_embedding_from_bytes,
    scan_cctv_for_person,
    load_known_faces
)
from app.services.cctv import cctv_manager, CCTVHandler
from app.websocket.manager import manager
from app.websocket.events import Events
import os

router = APIRouter(prefix="/missing-person", tags=["missing-person"])

# load known faces once on startup
known_faces = {}
active_searches: dict = {}


@router.on_event("startup")
async def load_faces():
    global known_faces
    known_faces = load_known_faces()
    print(f"[MissingPerson] {len(known_faces)} faces loaded into watchlist.")


@router.post("/search")
async def start_search(
    officer_id: str = Form(...),
    description: str = Form(""),
    photo: UploadFile = File(...)
):
    """
    Officer uploads photo → system scans database + CCTV for match.
    """
    photo_bytes = await photo.read()
    if not photo_bytes:
        raise HTTPException(status_code=400, detail="Empty photo.")

    # extract embedding from uploaded photo
    print(f"[MissingPerson] Extracting embedding from uploaded photo...")
    target_embedding = extract_embedding_from_bytes(photo_bytes)

    if target_embedding is None:
        raise HTTPException(
            status_code=422,
            detail="No face detected in photo. Please upload a clear front-facing photo."
        )

    # create search record
    search_id = str(uuid.uuid4())[:8]
    active_searches[search_id] = {
        "status": "scanning",
        "officer_id": officer_id,
        "description": description,
        "result": None
    }

    # notify officer scan started
    await manager.send_to_officer(officer_id, {
        "event": Events.MISSING_PERSON_SEARCH_STARTED,
        "search_id": search_id,
        "message": f"Face detected. Scanning database and {len(cctv_manager.list_cameras())} camera(s)..."
    })

    # build video path
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    video_path = os.path.join(base_dir, "data", "mock_cctv.mp4")

    # start scan for each camera
    for camera_id in cctv_manager.list_cameras():
        handler = CCTVHandler(
            source="file",
            camera_id=camera_id,
            file_path=video_path,
            frame_interval=0.3,
            max_frames=50
        )

        async def on_match(
            result,
            sid=search_id,
            oid=officer_id,
            cid=camera_id
        ):
            active_searches[sid]["status"] = "found"
            active_searches[sid]["result"] = result

            source_label = "database watchlist" if result.get("source") == "database" else f"CCTV camera {cid}"

            await manager.send_to_officer(oid, {
                "event": Events.MISSING_PERSON_FOUND,
                "search_id": sid,
                "camera_id": cid,
                "name": result.get("name", "Unknown"),
                "confidence": result["confidence"],
                "timestamp": result["timestamp"],
                "message": f"Person located on {source_label} with {result['confidence']}% confidence."
            })
            print(f"[MissingPerson] Match sent to officer {oid}")

        asyncio.create_task(
            scan_cctv_for_person(
                target_embedding=target_embedding,
                known_faces=known_faces,
                camera_id=camera_id,
                cctv_handler=handler,
                on_match=on_match,
                max_frames=50
            )
        )

    return {
        "search_id": search_id,
        "status": "scanning",
        "message": f"Scanning {len(known_faces)} known faces + {len(cctv_manager.list_cameras())} camera(s).",
        "cameras": cctv_manager.list_cameras()
    }


@router.get("/status/{search_id}")
async def get_search_status(search_id: str):
    search = active_searches.get(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Search not found.")
    return search


@router.get("/status")
async def list_searches():
    return {"searches": active_searches, "total": len(active_searches)}