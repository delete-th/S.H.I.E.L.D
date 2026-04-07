"""
Speech-to-Text service using OpenAI Whisper (runs locally, free).
Whisper model is loaded once at startup and reused.
"""
import io
import tempfile
import os
import whisper
from app.config import settings

# Load model at module import — this takes a few seconds on first run
_model: whisper.Whisper | None = None


def get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        print(f"[STT] Loading Whisper model: {settings.whisper_model}")
        _model = whisper.load_model(settings.whisper_model)
        print("[STT] Whisper model loaded.")
    return _model


async def transcribe(audio_bytes: bytes) -> str:
    """
    Transcribe raw audio bytes (webm/opus from browser MediaRecorder).
    Writes to a temp file because Whisper requires a file path.
    """
    model = get_model()

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        result = model.transcribe(tmp_path, language="en", fp16=False)
        transcript = result["text"].strip()
        return transcript
    finally:
        os.unlink(tmp_path)
