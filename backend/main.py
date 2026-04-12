import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.config import settings
from app.routers import audio, triage, tasks, cctv, coordination, intelligence
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


@app.on_event("startup")
async def setup_demo_cameras():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(base_dir, "app", "data", "mock_cctv.mp4")
    cctv_manager.add_camera("CAM-001", CCTVHandler(
        source="file",
        camera_id="CAM-001",
        file_path=video_path,
        frame_interval=0.5
    ))
    print(f"[CCTV] Registered. Path: {video_path}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "S.H.I.E.L.D"}


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
  </style>
</head>
<body>
  <h2>S.H.I.E.L.D — CCTV Test</h2>
  <button onclick="getSnapshot()">Get Snapshot</button>
  <button onclick="startStream()">Start Live Stream</button>
  <button onclick="stopStream()">Stop Stream</button>
  <br/><br/>
  <img id="feed" width="640" height="360" />
  <p id="status">Ready.</p>
  <script>
    let ws = null;
    const BASE = window.location.origin;
    const WS_BASE = BASE.replace("http", "ws");

    async function getSnapshot() {
      document.getElementById("status").innerText = "Fetching...";
      try {
        const res = await fetch(BASE + "/cctv/snapshot/CAM-001");
        const data = await res.json();
        document.getElementById("feed").src = "data:image/jpeg;base64," + data.image_base64;
        document.getElementById("status").innerText = "Snapshot: " + data.timestamp;
      } catch(e) {
        document.getElementById("status").innerText = "Error: " + e.message;
      }
    }

    function startStream() {
      if (ws) ws.close();
      const url = WS_BASE + "/ws/cctv/CAM-001";
      console.log("Connecting to:", url);
      document.getElementById("status").innerText = "Connecting to " + url;
      ws = new WebSocket(url);

      ws.onopen = () => {
        console.log("WebSocket opened");
        document.getElementById("status").innerText = "Streaming live...";
      };

      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.frame) {
          document.getElementById("feed").src = "data:image/jpeg;base64," + data.frame;
          document.getElementById("status").innerText = "Frame: " + data.timestamp;
        }
        if (data.event === "error") {
          document.getElementById("status").innerText = "Server error: " + data.message;
        }
      };

      ws.onerror = (err) => {
        console.error("WS error:", err);
        document.getElementById("status").innerText = "WebSocket error — see F12 console";
      };

      ws.onclose = (e) => {
        console.log("WS closed. Code:", e.code, "Reason:", e.reason);
        document.getElementById("status").innerText = "Stream stopped. Code: " + e.code;
      };
    }

    function stopStream() {
      if (ws) ws.close();
    }
  </script>
</body>
</html>
"""