"""
Missing Person Face Search Service

Supports three modes (auto-detected):
  1. Real-time upload  — officer uploads a photo; compared against watchlist DB
  2. Watchlist DB      — faces in app/data/faces/ (populated from uploads or LFW subset)
  3. CCTV scan         — scans live/recorded video frames for a target face

No mock data dependency. Falls back gracefully when DeepFace is unavailable.
"""
import os
import asyncio
import tempfile
import json
import uuid
import shutil
import numpy as np
from datetime import datetime
from typing import Optional, Callable

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    print("[FaceSearch] deepface not installed — face search disabled.")

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACES_DIR  = os.path.join(BASE_DIR, "data", "faces")
META_FILE  = os.path.join(BASE_DIR, "data", "faces_meta.json")  # name→info mapping
MODEL_NAME = "VGG-Face"
DETECTOR   = "opencv"
THRESHOLD  = 0.4    # cosine distance — lower = stricter match

os.makedirs(FACES_DIR, exist_ok=True)

# ── Metadata helpers ──────────────────────────────────────────────────────────

def load_meta() -> dict:
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_meta(meta: dict):
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

def register_face(image_bytes: bytes, name: str, notes: str = "") -> dict:
    """
    Save an uploaded face image to the watchlist.
    Returns { id, name, path, registered_at }
    """
    meta = load_meta()
    face_id = str(uuid.uuid4())[:8]
    safe_name = name.replace(" ", "_")
    filename = f"{safe_name}_{face_id}.jpg"
    path = os.path.join(FACES_DIR, filename)

    with open(path, "wb") as f:
        f.write(image_bytes)

    record = {
        "id": face_id,
        "name": name,
        "notes": notes,
        "path": path,
        "filename": filename,
        "registered_at": datetime.now().isoformat(),
    }
    meta[face_id] = record
    save_meta(meta)
    print(f"[FaceSearch] Registered face: {name} → {filename}")
    return record

def list_watchlist() -> list:
    meta = load_meta()
    return list(meta.values())

def remove_from_watchlist(face_id: str) -> bool:
    meta = load_meta()
    if face_id not in meta:
        return False
    rec = meta.pop(face_id)
    try:
        os.remove(rec["path"])
    except FileNotFoundError:
        pass
    save_meta(meta)
    return True

# ── Embedding helpers ──────────────────────────────────────────────────────────

def extract_embedding(image_path: str) -> Optional[np.ndarray]:
    if not DEEPFACE_AVAILABLE:
        return None
    try:
        result = DeepFace.represent(
            img_path=image_path,
            model_name=MODEL_NAME,
            detector_backend=DETECTOR,
            enforce_detection=True,
        )
        return np.array(result[0]["embedding"]) if result else None
    except Exception as e:
        print(f"[FaceSearch] Embedding error: {e}")
        return None

def extract_embedding_from_bytes(image_bytes: bytes) -> Optional[np.ndarray]:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    try:
        return extract_embedding(tmp_path)
    finally:
        os.unlink(tmp_path)

def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    n = np.linalg.norm(a) * np.linalg.norm(b)
    return round(float(1 - np.dot(a, b) / n), 4) if n else 1.0

# ── Watchlist scanning ────────────────────────────────────────────────────────

def load_known_faces() -> dict:
    """
    Load all watchlist faces and build { face_id: { name, embedding, ... } }.
    Skips files with no detectable face (logs a warning).
    """
    if not DEEPFACE_AVAILABLE:
        return {}
    known = {}
    meta  = load_meta()
    files = [f for f in os.listdir(FACES_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    print(f"[FaceSearch] Loading {len(files)} watchlist faces...")

    for filename in files:
        path = os.path.join(FACES_DIR, filename)
        # Find meta record by filename, or use filename as name
        rec  = next((r for r in meta.values() if r.get("filename") == filename), None)
        name = rec["name"] if rec else os.path.splitext(filename)[0].replace("_", " ")
        fid  = rec["id"]   if rec else filename

        emb  = extract_embedding(path)
        if emb is not None:
            known[fid] = {"name": name, "embedding": emb, "path": path}
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ No face detected: {filename}")

    print(f"[FaceSearch] {len(known)} faces ready.")
    return known

def search_database(target_embedding: np.ndarray, known_faces: dict) -> Optional[dict]:
    """Compare target against all watchlist faces. Return best match or None."""
    best_dist = THRESHOLD
    best      = None
    for fid, rec in known_faces.items():
        dist = cosine_distance(target_embedding, rec["embedding"])
        if dist < best_dist:
            best_dist = dist
            best = {
                "matched":    True,
                "face_id":    fid,
                "name":       rec["name"],
                "confidence": round((1 - dist) * 100, 1),
                "distance":   dist,
                "timestamp":  datetime.now().isoformat(),
                "source":     "watchlist",
            }
    return best

# ── CCTV frame scanning ───────────────────────────────────────────────────────

def _search_frame(frame_bytes: bytes, target_embedding: np.ndarray) -> Optional[dict]:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(frame_bytes)
        path = tmp.name
    try:
        if not DEEPFACE_AVAILABLE:
            return None
        faces = DeepFace.represent(
            img_path=path, model_name=MODEL_NAME,
            detector_backend=DETECTOR, enforce_detection=False,
        )
        if not faces:
            return None
        for fd in faces:
            emb  = np.array(fd["embedding"])
            dist = cosine_distance(target_embedding, emb)
            if dist <= THRESHOLD:
                return {
                    "matched":    True,
                    "confidence": round((1 - dist) * 100, 1),
                    "distance":   dist,
                    "timestamp":  datetime.now().isoformat(),
                    "face_region": fd.get("facial_area", {}),
                    "source":     "cctv",
                }
    except Exception as e:
        print(f"[FaceSearch] Frame error: {e}")
    finally:
        os.unlink(path)
    return None

async def scan_cctv_for_person(
    target_embedding: np.ndarray,
    known_faces: dict,
    camera_id: str,
    cctv_handler,
    on_match: Callable,
    max_frames: int = 60,
) -> None:
    """
    1. Check watchlist DB first (fast).
    2. Scan CCTV frames if no DB match.
    """
    loop = asyncio.get_event_loop()

    print(f"[FaceSearch] Checking watchlist for {camera_id}...")
    db_result = await loop.run_in_executor(None, search_database, target_embedding, known_faces)
    if db_result:
        print(f"[FaceSearch] Watchlist match: {db_result['name']} ({db_result['confidence']}%)")
        db_result.update({"camera_id": camera_id, "frame_number": 0, "frame_base64": ""})
        await on_match(db_result)
        return

    print(f"[FaceSearch] Scanning CCTV frames on {camera_id}...")
    count = 0
    async for frame in cctv_handler.stream_frames():
        if count >= max_frames:
            break
        result = await loop.run_in_executor(None, _search_frame, frame["jpeg_bytes"], target_embedding)
        count += 1
        if result:
            result.update({
                "camera_id":    camera_id,
                "frame_number": frame.get("frame_number", count),
                "frame_base64": frame.get("base64", ""),
            })
            await on_match(result)
            break
    print(f"[FaceSearch] Scan done. {count} frames checked.")