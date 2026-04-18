import os
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.config import settings
from app.routers import audio, triage, tasks, cctv, coordination, intelligence, escalation, pursuit, missing_person, report
from app.services.cctv import cctv_manager, CCTVHandler

app = FastAPI(
    title="S.H.I.E.L.D API",
    description="AI-powered dispatch for Certis security officers",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audio.router)
app.include_router(triage.router)
app.include_router(tasks.router)
app.include_router(cctv.router)
app.include_router(coordination.router)
app.include_router(intelligence.router)
app.include_router(escalation.router)
app.include_router(pursuit.router)
app.include_router(missing_person.router)
app.include_router(report.router)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.on_event("startup")
async def preload_stt_model():
    from app.services.stt import get_model
    import asyncio
    await asyncio.get_event_loop().run_in_executor(None, get_model)
    print("[STT] Model pre-loaded and ready.")


@app.on_event("startup")
async def setup_cameras():
    """
    Load cameras in this priority order:
      1. Cameras registered from Kaggle datasets (registered_cameras.json)
      2. Any .mp4/.avi files in app/data/cctv_feeds/ (manual uploads)
      3. Fallback: mock_cctv.mp4 as CAM-001
    """
    registered = 0
    repo_root = Path(BASE_DIR).parent
    backend_data_dir = Path(BASE_DIR) / "app" / "data"
    shared_data_dir = repo_root / "app" / "data"

    # ── 1. Kaggle-registered cameras ──────────────────────────────────────
    cam_reg_path = backend_data_dir / "registered_cameras.json"
    if not cam_reg_path.exists():
        cam_reg_path = shared_data_dir / "registered_cameras.json"

    if cam_reg_path.exists():
        try:
            registry = json.loads(Path(cam_reg_path).read_text())
            for cam_id, cam in registry.items():
                video_path = cam.get("video_path", "")
                if not os.path.exists(video_path):
                    print(f"[CCTV] Skipping {cam_id} — file not found: {video_path}")
                    continue
                cctv_manager.add_camera(cam_id, CCTVHandler(
                    source="file",
                    camera_id=cam_id,
                    file_path=video_path,
                    frame_interval=0.5,
                ))
                registered += 1
                print(f"[CCTV] Loaded registered camera: {cam_id} ({cam.get('label', '')})")
        except Exception as e:
            print(f"[CCTV] Could not load registered cameras: {e}")

    # ── 2. Manual video files in cctv_feeds/ ─────────────────────────────
    feeds_dir = backend_data_dir / "cctv_feeds"
    if not feeds_dir.is_dir():
        feeds_dir = shared_data_dir / "cctv_feeds"
    if feeds_dir.is_dir():
        exts = (".mp4", ".avi", ".mov", ".mkv")
        videos = sorted([
            f for f in Path(feeds_dir).rglob("*")
            if f.suffix.lower() in exts
        ])
        for i, video in enumerate(videos[:8]):  # max 8 manual feeds
            cam_id = f"CAM-FEED-{i+1:02d}"
            if cam_id in cctv_manager.cameras:
                continue  # already registered
            cctv_manager.add_camera(cam_id, CCTVHandler(
                source="file",
                camera_id=cam_id,
                file_path=str(video),
                frame_interval=0.5,
            ))
            registered += 1
            print(f"[CCTV] Loaded feed: {cam_id} → {video.name}")

    # ── 3. Fallback to mock ───────────────────────────────────────────────
    if registered == 0:
        mock_path = os.path.join(BASE_DIR, "app", "data", "mock_cctv.mp4")
        if os.path.exists(mock_path):
            cctv_manager.add_camera("CAM-001", CCTVHandler(
                source="file",
                camera_id="CAM-001",
                file_path=mock_path,
                frame_interval=0.5,
            ))
            print(f"[CCTV] Fallback: using mock_cctv.mp4 as CAM-001")
        else:
            print("[CCTV] WARNING: No video files found. CCTV feeds will be empty.")

    total = len(cctv_manager.list_cameras())
    print(f"[CCTV] {total} camera(s) active: {cctv_manager.list_cameras()}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "S.H.I.E.L.D", "cameras": cctv_manager.list_cameras()}


@app.get("/test", response_class=HTMLResponse)
async def test_page():
    return """
<!DOCTYPE html>
<html>
<head>
  <title>CCTV Test</title>
  <style>
    body { background: #111; color: white; font-family: monospace; padding: 20px; }
    img { border: 2px solid #e94560; border-radius: 8px; margin-top: 16px; display: block; }
    button { background: #e94560; color: white; border: none; padding: 10px 20px;
             cursor: pointer; border-radius: 6px; font-size: 14px; margin-right: 8px; }
    select { background: #1a1a2e; color: white; border: 1px solid #e94560;
             padding: 8px; border-radius: 6px; font-size: 14px; margin-right: 8px; }
  </style>
</head>
<body>
  <h2>S.H.I.E.L.D — CCTV Test</h2>
  <select id="cam-select"><option value="CAM-001">CAM-001</option></select>
  <button onclick="getSnapshot()">Snapshot</button>
  <button onclick="startStream()">Live Stream</button>
  <button onclick="stopStream()">Stop</button>
  <br/><br/>
  <img id="feed" width="640" height="360" />
  <p id="status">Ready.</p>
  <script>
    let ws = null;
    const BASE = window.location.origin;
    const WS_BASE = BASE.replace("http", "ws");

    // Populate camera dropdown from /cctv/cameras
    fetch(BASE + "/cctv/cameras").then(r => r.json()).then(d => {
      const sel = document.getElementById("cam-select");
      sel.innerHTML = d.cameras.map(c => `<option value="${c}">${c}</option>`).join("");
    });

    function getCam() { return document.getElementById("cam-select").value; }

    async function getSnapshot() {
      document.getElementById("status").innerText = "Fetching...";
      try {
        const res = await fetch(BASE + "/cctv/snapshot/" + getCam());
        const data = await res.json();
        document.getElementById("feed").src = "data:image/jpeg;base64," + data.image_base64;
        document.getElementById("status").innerText = "Snapshot: " + data.timestamp;
      } catch(e) {
        document.getElementById("status").innerText = "Error: " + e.message;
      }
    }

    function startStream() {
      if (ws) ws.close();
      const url = WS_BASE + "/ws/cctv/" + getCam();
      document.getElementById("status").innerText = "Connecting to " + url;
      ws = new WebSocket(url);
      ws.onopen  = () => { document.getElementById("status").innerText = "Streaming..."; };
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.frame) document.getElementById("feed").src = "data:image/jpeg;base64," + data.frame;
      };
      ws.onclose = () => { document.getElementById("status").innerText = "Stream stopped."; };
    }

    function stopStream() { if (ws) ws.close(); }
  </script>
</body>
</html>
"""