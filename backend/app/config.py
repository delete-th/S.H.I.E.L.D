from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Inworld TTS + Voice Cloning
    inworld_api_key: str = ""
    inworld_voice_id: str = ""   # set after running scripts/clone_jarvis_voice.py

    # Supabase
    supabase_url: str = "http://localhost:54321"
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Whisper
    whisper_model: str = "base"

    # OneMap (Singapore routing)
    onemap_api_key: str = ""
    onemap_base_url: str = "https://www.onemap.gov.sg"

    # Groq (cloud LLM — free tier, fast, no local GPU needed)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Ollama (local fallback — only used if groq_api_key is not set)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"

    # CORS
    # in app/config.py, update cors_origins
    cors_origins: List[str] = [
        "http://localhost:5173",  # React frontend
        "http://localhost:3000",  # alternative frontend
        "http://localhost:8001",  # backend test page
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
