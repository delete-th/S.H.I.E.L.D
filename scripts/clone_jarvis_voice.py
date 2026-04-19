#!/usr/bin/env python3
"""
Clone the JARVIS voice using Inworld AI voice cloning API.

Usage:
    python clone_jarvis_voice.py

Prerequisites:
    pip install httpx
    Set INWORLD_API_KEY in .env (same folder as this script, or parent folder)

After running, copy the printed INWORLD_VOICE_ID into your .env and restart the backend.

--- HOW TO GET YOUR API KEY ---
1. Go to https://studio.inworld.ai  (NOT platform.inworld.ai — that's deprecated)
2. Click your workspace name (top left) → "Integrations" → "API keys"
3. Copy the key — it looks like:  ab12cd34ef56...  (long hex string)
   OR a JWT:  eyJhbGci...
4. Paste it as INWORLD_API_KEY in your .env

--- AUTH FORMAT ---
Inworld has changed their auth format across API versions:
  v1 (old):  Authorization: Basic base64("key:")        ← trailing colon
  v1 (new):  Authorization: Basic base64("key:key")     ← key on both sides
  v2:        Authorization: Bearer <key>                 ← plain bearer
This script tries all three automatically.
"""
import base64
import os
import sys
import httpx
from pathlib import Path

# ── Locate audio files ────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent

# Search in script dir and one level up
def find_audio(name: str) -> Path | None:
    for search_dir in [SCRIPT_DIR, SCRIPT_DIR.parent]:
        p = search_dir / name
        if p.exists():
            return p
    return None

AUDIO_NAMES = ["JARVIS_CLONE.mp3"]
CLONE_URL   = "https://api.inworld.ai/voices/v1/voices:clone"

# ── Auth helpers ──────────────────────────────────────────────────────────────

def basic_colon(key: str) -> str:
    """Old format: base64('key:')"""
    return "Basic " + base64.b64encode(f"{key}:".encode()).decode()

def basic_double(key: str) -> str:
    """New format: base64('key:key')"""
    return "Basic " + base64.b64encode(f"{key}:{key}".encode()).decode()

def bearer(key: str) -> str:
    """Bearer token — used by some Inworld endpoints"""
    return f"Bearer {key}"

AUTH_FORMATS = [
    ("Basic base64(key:key) — recommended", basic_double),
    ("Bearer token",                         bearer),
    ("Basic base64(key:)  — legacy",         basic_colon),
]

# ── Key loader ────────────────────────────────────────────────────────────────

def load_api_key() -> str:
    # 1. Environment variable
    key = os.environ.get("INWORLD_API_KEY", "").strip()
    if key:
        return key

    # 2. .env files (script dir, parent, backend subdir)
    search_paths = [
        SCRIPT_DIR / ".env",
        SCRIPT_DIR.parent / ".env",
        SCRIPT_DIR.parent / "backend" / ".env",
    ]
    for env_path in search_paths:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("INWORLD_API_KEY=") and not line.startswith("#"):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    print(f"  Found INWORLD_API_KEY in {env_path}")
                    return key

    sys.exit(
        "\nERROR: INWORLD_API_KEY not found.\n"
        "Options:\n"
        "  1. export INWORLD_API_KEY=your_key_here  (then re-run)\n"
        "  2. Add INWORLD_API_KEY=your_key_here to your .env file\n"
        "\nGet your key at: https://studio.inworld.ai → Workspace → Integrations → API keys\n"
    )

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Load key
    api_key = load_api_key()
    print(f"  Key loaded: {api_key[:6]}...{api_key[-4:]}  ({len(api_key)} chars)")

    # Diagnose key type
    if api_key.startswith("eyJ"):
        print("  Key type: JWT token — will try Bearer first")
        AUTH_FORMATS.insert(0, AUTH_FORMATS.pop(1))  # move Bearer to front
    elif len(api_key) < 20:
        print(f"\nWARNING: Key looks very short ({len(api_key)} chars). Double-check it's the full key.\n")

    # Find audio files
    audio_files = []
    for name in AUDIO_NAMES:
        path = find_audio(name)
        if path:
            audio_files.append(path)
        else:
            print(f"  WARNING: Could not find '{name}' — skipping")

    if not audio_files:
        sys.exit(
            "\nERROR: No audio files found.\n"
            f"Expected files in {SCRIPT_DIR} or {SCRIPT_DIR.parent}:\n"
            + "\n".join(f"  • {n}" for n in AUDIO_NAMES)
        )

    # Build voice samples
    print(f"\nBuilding voice samples from {len(audio_files)} audio clip(s)...")
    voice_samples = []
    for f in audio_files:
        raw  = f.read_bytes()
        b64  = base64.b64encode(raw).decode()
        size_kb = len(raw) // 1024
        print(f"  + {f.name}  ({size_kb} KB raw  /  {len(b64)//1024} KB base64)")

        # Inworld recommends clips under 5 MB raw for best quality
        if size_kb > 5120:
            print(f"    NOTE: This file is large ({size_kb} KB). Inworld works best with clips under 5 MB.")

        voice_samples.append({"audioData": b64})

    payload = {
        "displayName": "JARVIS",
        "langCode":    "EN_US",
        "description": "S.H.I.E.L.D dispatch AI — JARVIS voice clone",
        "voiceSamples": voice_samples,
        "audioProcessingConfig": {"removeBackgroundNoise": True},
    }

    # Try each auth format until one works
    last_error = ""
    for fmt_name, fmt_fn in AUTH_FORMATS:
        print(f"\nTrying auth format: {fmt_name} ...")
        headers = {
            "Authorization": fmt_fn(api_key),
            "Content-Type":  "application/json",
        }
        try:
            with httpx.Client(timeout=180.0) as client:
                resp = client.post(CLONE_URL, headers=headers, json=payload)
        except httpx.TimeoutException:
            print("  Request timed out — server may be busy, try again.")
            continue
        except httpx.ConnectError as e:
            sys.exit(f"\nERROR: Could not connect to Inworld API.\nCheck internet connection.\nDetails: {e}")

        print(f"  HTTP {resp.status_code}")

        if resp.status_code == 200:
            _handle_success(resp)
            return

        if resp.status_code in (401, 403):
            last_error = resp.text
            print(f"  Auth failed: {resp.text[:120]}")
            continue  # try next format

        if resp.status_code == 400:
            print(f"\nERROR 400 — Bad request (auth passed, but payload rejected):\n{resp.text}")
            _suggest_fixes(resp.text)
            sys.exit(1)

        if resp.status_code == 429:
            sys.exit("\nERROR 429 — Rate limited. Wait a few minutes and try again.")

        # Unexpected status
        sys.exit(f"\nERROR: Inworld returned {resp.status_code}:\n{resp.text}")

    # All formats failed
    print(f"\nERROR: All auth formats failed. Last response:\n{last_error}")
    print(
        "\nTROUBLESHOOTING:\n"
        "1. Verify your key at https://studio.inworld.ai → Workspace → Integrations → API keys\n"
        "2. Make sure you copied the FULL key (no leading/trailing spaces)\n"
        "3. Check the key has voice cloning permission enabled in the Inworld dashboard\n"
        "4. Try creating a new API key — old keys may have restricted scopes\n"
        "5. The voice cloning API requires a paid/Pro Inworld account\n"
    )
    sys.exit(1)


def _handle_success(resp):
    data     = resp.json()
    voice    = data.get("voice", {})
    voice_id = voice.get("voiceId", "") or voice.get("name", "")

    if not voice_id:
        # Some versions return the ID at top level
        voice_id = data.get("voiceId", "") or data.get("name", "")

    if not voice_id:
        print(f"\nWARNING: Got 200 OK but could not find voiceId in response:")
        print(data)
        return

    # Validation warnings
    for sample in data.get("audioSamplesValidated", []):
        for err in sample.get("errors", []):
            print(f"  SAMPLE ERROR: {err}")
        for warn in sample.get("warnings", []):
            print(f"  SAMPLE WARNING: {warn}")

    print(f"\n{'='*50}")
    print(f"  JARVIS voice cloned successfully!")
    print(f"  Voice ID: {voice_id}")
    print(f"{'='*50}")
    print(f"\nAdd this to your .env file and restart the backend:\n")
    print(f"  INWORLD_VOICE_ID={voice_id}\n")

    # Offer to write it directly
    env_paths = [
        SCRIPT_DIR / ".env",
        SCRIPT_DIR.parent / ".env",
        SCRIPT_DIR.parent / "backend" / ".env",
    ]
    for env_path in env_paths:
        if not env_path.exists():
            continue
        content = env_path.read_text(encoding="utf-8")
        if "INWORLD_VOICE_ID=" in content:
            import re
            updated = re.sub(r"INWORLD_VOICE_ID=.*", f"INWORLD_VOICE_ID={voice_id}", content)
            env_path.write_text(updated, encoding="utf-8")
            print(f"  Auto-updated {env_path}")
        else:
            with env_path.open("a", encoding="utf-8") as f:
                f.write(f"\nINWORLD_VOICE_ID={voice_id}\n")
            print(f"  Appended to {env_path}")
        break


def _suggest_fixes(error_text: str):
    error_lower = error_text.lower()
    if "audio" in error_lower or "sample" in error_lower:
        print(
            "\nSUGGESTION: Audio format issue.\n"
            "• Inworld requires MP3 or WAV, 16kHz+, mono or stereo\n"
            "• Each clip should be 30 seconds–5 minutes of clean speech\n"
            "• Avoid music, background noise, or multiple speakers\n"
        )
    if "lang" in error_lower:
        print("\nSUGGESTION: Try changing langCode to 'en-US' (lowercase with hyphen)")


if __name__ == "__main__":
    main()