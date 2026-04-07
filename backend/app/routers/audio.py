"""
WebSocket endpoint: /ws/audio

Flow:
  1. Client connects and sends raw audio bytes (webm/opus from MediaRecorder)
  2. Whisper transcribes the audio
  3. Check Redis cache for this transcript
  4. If cache miss → Ollama/Mistral triages the transcript
  5. Cache the result
  6. ElevenLabs synthesizes a TTS audio response
  7. Send transcript + triage JSON back, then stream TTS audio
"""
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services import stt, llm, tts, cache

router = APIRouter()


@router.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Client connected")

    try:
        while True:
            # Receive audio binary from client
            audio_bytes = await websocket.receive_bytes()

            if not audio_bytes:
                continue

            # Step 1: Transcribe
            try:
                transcript = await stt.transcribe(audio_bytes)
            except Exception as e:
                await websocket.send_json({"type": "error", "message": f"STT failed: {e}"})
                continue

            if not transcript:
                await websocket.send_json({"type": "error", "message": "No speech detected."})
                continue

            # Send transcript back immediately
            await websocket.send_json({"type": "transcript", "text": transcript})

            # Step 2: Check cache
            result = await cache.get_cached(transcript)

            # Step 3: Triage via Ollama if cache miss
            if result is None:
                try:
                    result = await llm.triage_transcript(transcript)
                    await cache.set_cached(transcript, result)
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"LLM failed: {e}"})
                    continue

            # Send triage result
            await websocket.send_json({"type": "triage", "result": result.model_dump()})

            # Step 4: Synthesize TTS
            tts_text = tts.build_tts_text(result)
            try:
                audio_data = await tts.synthesize(tts_text)
                if audio_data:
                    audio_b64 = base64.b64encode(audio_data).decode()
                    await websocket.send_json({"type": "audio", "data": audio_b64})
            except Exception as e:
                print(f"[TTS] Error: {e}")

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Unexpected error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
