"""
Text-to-Speech service using Inworld AI API.

Primary:  HTTP streaming  POST https://api.inworld.ai/tts/v1/voice:stream
          → yields MP3 chunks as they arrive (low latency)
Fallback: Non-streaming   POST https://api.inworld.ai/tts/v1/voice
          → returns full MP3 in one response

Auth: Authorization: Basic <api-key>  (key is already base64-encoded by Inworld)
"""
import base64
import json
import httpx
from typing import AsyncGenerator
from app.config import settings

_TTS_URL        = "https://api.inworld.ai/tts/v1/voice"
_TTS_STREAM_URL = "https://api.inworld.ai/tts/v1/voice:stream"
_MODEL_ID       = "inworld-tts-1.5-max"


def _headers() -> dict:
    return {
        "Authorization": f"Basic {settings.inworld_api_key}",
        "Content-Type": "application/json",
    }


def _configured() -> bool:
    if not settings.inworld_api_key or not settings.inworld_voice_id:
        print("[TTS] Inworld API key or voice ID not set — skipping TTS.")
        return False
    return True


async def synthesize_stream(text: str) -> AsyncGenerator[bytes, None]:
    """Yield MP3 bytes chunks as they stream from Inworld. Preferred for interactive use."""
    if not _configured():
        return

    payload = {
        "text": text,
        "voice_id": settings.inworld_voice_id,
        "model_id": _MODEL_ID,
        "audio_config": {
            "audio_encoding": "MP3",
            "speaking_rate": 1,
        },
        "temperature": 1,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", _TTS_STREAM_URL, headers=_headers(), json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    audio_b64 = data.get("result", {}).get("audioContent", "")
                    if audio_b64:
                        yield base64.b64decode(audio_b64)
                except (json.JSONDecodeError, KeyError):
                    continue


async def synthesize(text: str) -> bytes:
    """Non-streaming fallback — returns full MP3 bytes in one response."""
    if not _configured():
        return b""

    payload = {
        "text": text,
        "voiceId": settings.inworld_voice_id,
        "modelId": _MODEL_ID,
        "audioConfig": {
            "speakingRate": 1,
        },
        "temperature": 1,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(_TTS_URL, headers=_headers(), json=payload)
        response.raise_for_status()

    audio_b64 = response.json().get("audioContent", "")
    return base64.b64decode(audio_b64) if audio_b64 else b""


def build_tts_text(result) -> str:
    """Format triage result into a concise spoken response."""
    priority_word = {"high": "HIGH PRIORITY", "medium": "MEDIUM PRIORITY", "low": "LOW PRIORITY"}
    p = priority_word.get(result.priority, "")
    return f"{p}. {result.action}. {result.summary}"
