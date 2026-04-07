"""
Text-to-Speech service using ElevenLabs API.
Falls back to an empty bytes response if the API key is not configured.
"""
import httpx
from app.config import settings


async def synthesize(text: str) -> bytes:
    """Convert text to speech audio bytes (MP3) via ElevenLabs."""
    if not settings.elevenlabs_api_key:
        print("[TTS] ElevenLabs API key not set — skipping TTS.")
        return b""

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"

    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.content


def build_tts_text(result) -> str:
    """Format triage result into a concise spoken response."""
    priority_word = {"high": "HIGH PRIORITY", "medium": "MEDIUM PRIORITY", "low": "LOW PRIORITY"}
    p = priority_word.get(result.priority, "")
    return f"{p}. {result.action}. {result.summary}"
