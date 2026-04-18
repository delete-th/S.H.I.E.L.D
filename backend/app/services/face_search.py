"""
Missing Person Face Search Service

Demo flow:
1. Officer uploads photo of missing person
2. DeepFace extracts face embedding from photo
3. System compares against known faces database (app/data/faces/)
4. If match found in database → simulate CCTV detection
5. Notify officer via WebSocket with camera location
"""
import os
import asyncio
import tempfile
import numpy as np
from datetime import datetime
from typing import Optional, Callable

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    print("[FaceSearch] deepface not installed — face search disabled.")

# --- Configuration ---
FACES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "faces"
)
MODEL_NAME = "VGG-Face"
DETECTOR = "opencv"
MATCH_THRESHOLD = 0.4


def extract_embedding(image_path: str) -> Optional[np.ndarray]:
    """Extract face embedding from an image file path."""
    if not DEEPFACE_AVAILABLE:
        return None
    try:
        result = DeepFace.represent(
            img_path=image_path,
            model_name=MODEL_NAME,
            detector_backend=DETECTOR,
            enforce_detection=True
        )
        if result:
            return np.array(result[0]["embedding"])
    except Exception as e:
        print(f"[FaceSearch] Embedding error: {e}")
    return None


def extract_embedding_from_bytes(image_bytes: bytes) -> Optional[np.ndarray]:
    """Extract face embedding from raw image bytes."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    try:
        return extract_embedding(tmp_path)
    finally:
        os.unlink(tmp_path)


def compare_faces(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """
    Compare two embeddings using cosine distance.
    Returns 0.0 (identical) to 1.0 (completely different).
    """
    dot = np.dot(emb1, emb2)
    norm = np.linalg.norm(emb1) * np.linalg.norm(emb2)
    if norm == 0:
        return 1.0
    return round(1 - (dot / norm), 4)


def is_match(distance: float) -> bool:
    return distance <= MATCH_THRESHOLD


def load_known_faces() -> dict:
    """
    Load all face images from app/data/faces/ and extract embeddings.
    Returns { name: embedding } — acts as missing persons watchlist.
    """
    known = {}
    if not os.path.exists(FACES_DIR):
        print(f"[FaceSearch] Faces directory not found: {FACES_DIR}")
        return known

    image_files = [
        f for f in os.listdir(FACES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    print(f"[FaceSearch] Loading {len(image_files)} known faces...")
    for filename in image_files:
        path = os.path.join(FACES_DIR, filename)
        name = os.path.splitext(filename)[0].replace("_", " ")
        embedding = extract_embedding(path)
        if embedding is not None:
            known[name] = embedding
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ No face detected: {filename}")

    print(f"[FaceSearch] {len(known)} faces ready.")
    return known


def search_database_for_person(
    target_embedding: np.ndarray,
    known_faces: dict
) -> Optional[dict]:
    """
    Compare target embedding against all known faces in database.
    Returns best match info or None if no match found.
    """
    best_match = None
    best_distance = 1.0

    for name, embedding in known_faces.items():
        distance = compare_faces(target_embedding, embedding)
        print(f"[FaceSearch] Comparing with {name}: distance={distance}")
        if is_match(distance) and distance < best_distance:
            best_distance = distance
            best_match = {
                "matched": True,
                "name": name,
                "confidence": round((1 - distance) * 100, 1),
                "distance": distance,
                "timestamp": datetime.now().isoformat()
            }

    return best_match


async def scan_cctv_for_person(
    target_embedding: np.ndarray,
    known_faces: dict,
    camera_id: str,
    cctv_handler,
    on_match: Callable,
    max_frames: int = 50
) -> None:
    """
    Two-step scan:
    1. Check uploaded photo against known faces database first (fast)
    2. If no match in database, scan actual CCTV frames (slower)
    """
    print(f"[FaceSearch] Step 1 — checking database for {camera_id}...")

    # Step 1 — check against known faces database
    loop = asyncio.get_event_loop()
    db_result = await loop.run_in_executor(
        None,
        search_database_for_person,
        target_embedding,
        known_faces
    )

    if db_result:
        print(f"[FaceSearch] Database match: {db_result['name']} ({db_result['confidence']}%)")
        db_result["camera_id"] = camera_id
        db_result["frame_number"] = 0
        db_result["frame_base64"] = ""
        db_result["source"] = "database"
        await on_match(db_result)
        return

    # Step 2 — scan actual CCTV frames if no database match
    print(f"[FaceSearch] Step 2 — scanning CCTV frames on {camera_id}...")
    frames_checked = 0

    async for frame in cctv_handler.stream_frames():
        if frames_checked >= max_frames:
            break

        result = await loop.run_in_executor(
            None,
            _search_frame,
            frame["jpeg_bytes"],
            target_embedding
        )

        frames_checked += 1
        print(f"[FaceSearch] Frame {frames_checked}/{max_frames} checked.")

        if result:
            result["camera_id"] = camera_id
            result["frame_number"] = frame["frame_number"]
            result["frame_base64"] = frame["base64"]
            result["source"] = "cctv"
            await on_match(result)
            break

    print(f"[FaceSearch] Scan complete. {frames_checked} frames checked.")


def _search_frame(
    frame_bytes: bytes,
    target_embedding: np.ndarray
) -> Optional[dict]:
    """Search a single CCTV frame for a face match."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(frame_bytes)
        frame_path = tmp.name

    try:
        if not DEEPFACE_AVAILABLE:
            return None
        faces = DeepFace.represent(
            img_path=frame_path,
            model_name=MODEL_NAME,
            detector_backend=DETECTOR,
            enforce_detection=False
        )
        if not faces:
            return None

        for face_data in faces:
            frame_embedding = np.array(face_data["embedding"])
            distance = compare_faces(target_embedding, frame_embedding)
            if is_match(distance):
                return {
                    "matched": True,
                    "confidence": round((1 - distance) * 100, 1),
                    "distance": distance,
                    "timestamp": datetime.now().isoformat(),
                    "face_region": face_data.get("facial_area", {})
                }
    except Exception as e:
        print(f"[FaceSearch] Frame search error: {e}")
    finally:
        os.unlink(frame_path)

    return None