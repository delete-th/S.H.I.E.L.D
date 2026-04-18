"""
Speech-to-Text using faster-whisper (Python 3.12 compatible).
Drop-in replacement for openai-whisper — same interface, faster performance.
"""
import tempfile
import os
from faster_whisper import WhisperModel
from app.config import settings

_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        print(f"[STT] Loading faster-whisper model: {settings.whisper_model}")
        # device="cpu", compute_type="int8" — works on any Windows machine
        _model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        print("[STT] Model loaded.")
    return _model


def _run_transcribe(audio_bytes: bytes) -> str:
    model = get_model()
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        segments, _ = model.transcribe(tmp_path, language="en")
        return " ".join(segment.text for segment in segments).strip()
    finally:
        os.unlink(tmp_path)


async def transcribe(audio_bytes: bytes) -> str:
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_transcribe, audio_bytes)