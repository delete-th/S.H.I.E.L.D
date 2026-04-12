from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.services.cctv import CCTVHandler, cctv_manager
from app.websocket.events import Events
import os

router = APIRouter(tags=["cctv"])


@router.get("/cctv/cameras")
async def list_cameras():
    return {
        "cameras": cctv_manager.list_cameras(),
        "total": len(cctv_manager.list_cameras())
    }


@router.get("/cctv/snapshot/{camera_id}")
async def get_snapshot(camera_id: str):
    handler = cctv_manager.get_camera(camera_id)
    if not handler:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found.")
    frame = handler.extract_single_frame()
    if not frame:
        raise HTTPException(status_code=503, detail="Could not capture frame.")
    return {
        "camera_id": camera_id,
        "timestamp": frame["timestamp"],
        "image_base64": frame["base64"]
    }


@router.websocket("/ws/cctv/{camera_id}")
async def stream_cctv(websocket: WebSocket, camera_id: str):
    await websocket.accept()
    print(f"[CCTV WS] Client connected to {camera_id}")

    handler = cctv_manager.get_camera(camera_id)
    if not handler:
        await websocket.send_json({
            "event": "error",
            "message": f"Camera {camera_id} not found."
        })
        await websocket.close()
        return

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    video_path = os.path.join(base_dir, "data", "mock_cctv.mp4")

    stream_handler = CCTVHandler(
        source=handler.source,
        camera_id=camera_id,
        file_path=video_path,
        frame_interval=0.5
    )

    try:
        async for frame in stream_handler.stream_frames():
            try:
                await websocket.send_json({
                    "event": Events.CCTV_FRAME,
                    "camera_id": camera_id,
                    "timestamp": frame["timestamp"],
                    "frame": frame["base64"]
                })
            except Exception as e:
                print(f"[CCTV WS] Send error: {e}")
                break

    except WebSocketDisconnect:
        print(f"[CCTV WS] Client disconnected from {camera_id}")
    except Exception as e:
        print(f"[CCTV WS] Error: {e}")
    finally:
        stream_handler.stop()
        print(f"[CCTV WS] Stream ended for {camera_id}")