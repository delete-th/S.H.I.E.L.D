#!/usr/bin/env python3
"""
Clone the JARVIS voice using Inworld AI voice cloning API.

Usage:
    python scripts/clone_jarvis_voice.py

Prerequisites:
    pip install httpx
    Set INWORLD_API_KEY in .env or as an environment variable.
    Get your API key at: https://platform.inworld.ai

After running, copy the printed INWORLD_VOICE_ID into your .env and restart the backend.

Inworld voice cloning docs:
    POST https://api.inworld.ai/voices/v1/voices:clone
    Auth: Basic base64(apiKey:)
    Body: { displayName, langCode, voiceSamples: [{ audioData: base64, transcription? }] }
"""
import base64
import os
import sys
import httpx
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
AUDIO_FILES = [
    REPO_ROOT / "JARVIS (1).mp3",
    REPO_ROOT / "JARVIS II.mp3",
    REPO_ROOT / "Jarvis audio 4.mp3",
]
CLONE_URL = "https://api.inworld.ai/voices/v1/voices:clone"


def load_api_key() -> str:
    key = os.environ.get("INWORLD_API_KEY", "")
    if not key:
        for env_path in [REPO_ROOT / "backend" / ".env", REPO_ROOT / ".env"]:
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("INWORLD_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                if key:
                    break
    if not key:
        sys.exit("ERROR: INWORLD_API_KEY not set. Add it to backend/.env or export it.\n"
                 "Get your key at: https://platform.inworld.ai")
    return key


def auth_header(api_key: str) -> str:
    # Inworld: Basic base64(apiKey:)  — trailing colon is required
    encoded = base64.b64encode(f"{api_key}:".encode()).decode()
    return f"Basic {encoded}"


def main():
    api_key = load_api_key()

    missing = [str(f) for f in AUDIO_FILES if not f.exists()]
    if missing:
        sys.exit("ERROR: Audio file(s) not found:\n" + "\n".join(missing))

    print("Building voice samples from JARVIS audio clips...")
    voice_samples = []
    for f in AUDIO_FILES:
        audio_b64 = base64.b64encode(f.read_bytes()).decode()
        voice_samples.append({"audioData": audio_b64})
        print(f"  + {f.name} ({len(audio_b64) // 1024} KB base64)")

    payload = {
        "displayName": "JARVIS",
        "langCode": "EN_US",
        "description": "S.H.I.E.L.D dispatch AI — JARVIS voice clone",
        "voiceSamples": voice_samples,
        "audioProcessingConfig": {
            "removeBackgroundNoise": True,
        },
    }

    print("\nUploading to Inworld AI...")
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            CLONE_URL,
            headers={
                "Authorization": auth_header(api_key),
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.status_code != 200:
        sys.exit(f"ERROR: Inworld returned {response.status_code}:\n{response.text}")

    data = response.json()
    voice = data.get("voice", {})
    voice_id = voice.get("voiceId", "")

    if not voice_id:
        sys.exit(f"ERROR: No voiceId in response:\n{data}")

    # Check for validation warnings
    for sample in data.get("audioSamplesValidated", []):
        if sample.get("errors"):
            print(f"  WARNING — sample errors: {sample['errors']}")
        if sample.get("warnings"):
            print(f"  Note — sample warnings: {sample['warnings']}")

    print(f"\nJARVIS voice cloned successfully!")
    print(f"Voice ID: {voice_id}")
    print(f"\nAdd this to your backend/.env file:")
    print(f"INWORLD_VOICE_ID={voice_id}")


if __name__ == "__main__":
    main()
