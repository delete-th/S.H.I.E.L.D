#!/usr/bin/env python3
"""
Downloads real CCTV/surveillance footage datasets from Kaggle
and registers each video as a named camera feed in S.H.I.E.L.D.

Prerequisites:
    pip install kaggle
    Set up ~/.kaggle/kaggle.json with your Kaggle API key:
      { "username": "YOUR_USERNAME", "key": "YOUR_API_KEY" }
    Get your key at: https://www.kaggle.com/settings → API → Create New Token

Usage:
    python setup_cctv_dataset.py
    python setup_cctv_dataset.py --dataset ucf-crime    # specific dataset
    python setup_cctv_dataset.py --list                 # list registered cameras

Datasets downloaded (choose based on use case):

  1. ucf-crime
        — Replacement for UCF Crime
        — CCTV-style violence vs non‑violence scenes
        — Uses: anomaly detection, violence detection

  2. mot-challenge
        — MOT15 pedestrian tracking dataset
        — Multi-camera surveillance sequences
        — Uses: tracking, multi-object detection

  3. violence-detection
        — Smart City CCTV violence detection dataset
        — Real CCTV footage with violent vs non‑violent events
        — Uses: security event classification

  4. real-life-violence
        — Real-Life Violence Situations Dataset
        — CCTV-style violence vs non‑violence scenes
        — Uses: binary violence classification

  5. fire-detection
        — Fire Detection from CCTV
        — Fire vs non‑fire surveillance footage
        — Uses: fire/smoke anomaly detection
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent
DATA_DIR    = BASE_DIR / "app" / "data"
CCTV_DIR    = DATA_DIR / "cctv_feeds"
CAM_REG     = DATA_DIR / "registered_cameras.json"

# ── Kaggle datasets ──────────────────────────────────────────────────────────

DATASETS = {
    "ucf-crime": {
        "kaggle_id": "mohamedmustafa/real-life-violence-situations-dataset",
        "description": "Replacement for UCF Crime — CCTV-style violence vs non-violence scenes",
        "cameras": [
            {"id": "CAM-UCF-01", "label": "Violence Scene", "file_glob": "Violence/*.mp4"},
            {"id": "CAM-UCF-02", "label": "Violence Scene (AVI)", "file_glob": "Violence/*.avi"},
            {"id": "CAM-UCF-03", "label": "Normal Scene", "file_glob": "NonViolence/*.mp4"},
            {"id": "CAM-UCF-04", "label": "Normal Scene (AVI)", "file_glob": "NonViolence/*.avi"},
        ],
    },

    "mot-challenge": {
        "kaggle_id": "mdraselsarker/mot15-challenge-dataset",
        "description": "Multi-camera pedestrian tracking dataset",
        "cameras": [
            {"id": "CAM-MOT-01", "label": "Entrance",  "file_glob": "*.mp4"},
            {"id": "CAM-MOT-02", "label": "Corridor",  "file_glob": "*.avi"},
        ],
    },

    "violence-detection": {
        "kaggle_id": "toluwaniaremu/smartcity-cctv-violence-detection-dataset-scvd",
        "description": "Smart City CCTV violence detection dataset",
        "cameras": [
            {"id": "CAM-VD-01", "label": "Violence Scene", "file_glob": "*.mp4"},
            {"id": "CAM-VD-02", "label": "Violence Scene (AVI)", "file_glob": "*.avi"},
        ],
    },

    "real-life-violence": {
        "kaggle_id": "mohamedmustafa/real-life-violence-situations-dataset",
        "description": "Real-Life Violence Situations Dataset — CCTV-style violence vs non-violence scenes",
        "cameras": [
            {"id": "CAM-RLV-01", "label": "Violence Scene", "file_glob": "Violence/*.mp4"},
            {"id": "CAM-RLV-02", "label": "Violence Scene (AVI)", "file_glob": "Violence/*.avi"},
            {"id": "CAM-RLV-03", "label": "Normal Scene", "file_glob": "NonViolence/*.mp4"},
            {"id": "CAM-RLV-04", "label": "Normal Scene (AVI)", "file_glob": "NonViolence/*.avi"},
        ],
    },

    "fire-detection": {
        "kaggle_id": "ritupande/fire-detection-from-cctv",
        "description": "Fire Detection from CCTV — fire vs non-fire surveillance footage",
        "cameras": [
            {"id": "CAM-FIRE-01", "label": "Fire Detected", "file_glob": "Fire/*.mp4"},
            {"id": "CAM-FIRE-02", "label": "Fire Detected (AVI)", "file_glob": "Fire/*.avi"},
            {"id": "CAM-FIRE-03", "label": "Normal Scene", "file_glob": "Non-Fire/*.mp4"},
            {"id": "CAM-FIRE-04", "label": "Normal Scene (AVI)", "file_glob": "Non-Fire/*.avi"},
        ],
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def check_kaggle():
    try:
        import kaggle  # noqa
        return True
    except ImportError:
        print("ERROR: kaggle package not installed. Run: pip install kaggle")
        sys.exit(1)

def check_kaggle_auth():
    creds = Path.home() / ".kaggle" / "kaggle.json"
    if not creds.exists():
        sys.exit(
            "ERROR: Kaggle credentials not found.\n"
            "1. Go to https://www.kaggle.com/settings → API → Create New Token\n"
            "2. Save the downloaded kaggle.json to ~/.kaggle/kaggle.json\n"
            "3. Run: chmod 600 ~/.kaggle/kaggle.json"
        )

def load_registry() -> dict:
    if CAM_REG.exists():
        try:
            return json.loads(CAM_REG.read_text())
        except Exception:
            pass
    return {}

def save_registry(reg: dict):
    CAM_REG.parent.mkdir(parents=True, exist_ok=True)
    CAM_REG.write_text(json.dumps(reg, indent=2))

def find_videos(directory: Path, glob: str) -> list[Path]:
    """Find video files matching glob pattern recursively."""
    results = []
    for pattern in [glob, "**/" + glob]:
        results.extend(directory.glob(pattern))
    # Also find any mp4/avi if specific glob finds nothing
    if not results:
        for ext in ["**/*.mp4", "**/*.avi", "**/*.mov", "**/*.mkv"]:
            results.extend(directory.glob(ext))
    return sorted(results)[:10]  # max 10 files

def download_dataset(name: str):
    ds = DATASETS.get(name)
    if not ds:
        print(f"Unknown dataset: {name}. Available: {', '.join(DATASETS.keys())}")
        return

    dest = CCTV_DIR / name
    dest.mkdir(parents=True, exist_ok=True)

    print(f"\nDownloading: {ds['description']}")
    print(f"  Kaggle ID: {ds['kaggle_id']}")
    print(f"  Destination: {dest}")

    try:
        result = subprocess.run(
            ["kaggle", "datasets", "download", "-d", ds["kaggle_id"],
             "--unzip", "--path", str(dest)],
            capture_output=False, check=True,
        )
        print("  ✓ Download complete")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Download failed: {e}")
        print("  → Check dataset ID at https://www.kaggle.com/datasets")
        return

    # Register cameras
    reg = load_registry()
    registered = 0
    for cam in ds["cameras"]:
        videos = find_videos(dest, cam["file_glob"])
        if not videos:
            print(f"  ⚠ No videos found for {cam['id']} (glob: {cam['file_glob']})")
            continue
        video_path = str(videos[0])
        reg[cam["id"]] = {
            "id":          cam["id"],
            "label":       cam["label"],
            "dataset":     name,
            "video_path":  video_path,
            "status":      "online",
        }
        print(f"  ✓ Registered {cam['id']} → {Path(video_path).name}")
        registered += 1

    save_registry(reg)
    print(f"\n✅ {registered} cameras registered from {name}")
    print_next_steps()


def list_cameras():
    reg = load_registry()
    if not reg:
        print("No cameras registered. Run: python setup_cctv_dataset.py")
        return
    print(f"\n{'ID':<20} {'Label':<20} {'Dataset':<20} {'File'}")
    print("-" * 80)
    for cam in reg.values():
        fname = Path(cam["video_path"]).name if cam.get("video_path") else "—"
        print(f"{cam['id']:<20} {cam['label']:<20} {cam.get('dataset','—'):<20} {fname}")
    print(f"\nTotal: {len(reg)} cameras")


def print_next_steps():
    print("\n── Next steps ──────────────────────────────────────────────────────────")
    print("1. Update app/main.py to load registered cameras at startup:")
    print("   from app.data.setup_cctv_dataset import load_registry")
    print("   for cam_id, cam in load_registry().items():")
    print("       cctv_manager.add_camera(cam_id, CCTVHandler(")
    print('           source="file", camera_id=cam_id,')
    print('           file_path=cam["video_path"], frame_interval=0.5')
    print("       ))")
    print("2. Restart the backend — cameras will appear in the CCTV panel")
    print("3. The frontend auto-fetches /cctv/cameras and shows them all")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="S.H.I.E.L.D CCTV dataset manager")
    parser.add_argument("--dataset", choices=list(DATASETS.keys()), help="Dataset to download")
    parser.add_argument("--all",     action="store_true", help="Download all datasets")
    parser.add_argument("--list",    action="store_true", help="List registered cameras")
    args = parser.parse_args()

    if args.list:
        list_cameras()
        return

    check_kaggle()
    check_kaggle_auth()

    if args.all:
        for name in DATASETS:
            download_dataset(name)
    elif args.dataset:
        download_dataset(args.dataset)
    else:
        print("Available datasets:")
        for name, ds in DATASETS.items():
            print(f"  {name:<20} — {ds['description']}")
        print("\nUsage: python setup_cctv_dataset.py --dataset ucf-crime")
        print("       python setup_cctv_dataset.py --all")
        print("       python setup_cctv_dataset.py --list")


if __name__ == "__main__":
    main()