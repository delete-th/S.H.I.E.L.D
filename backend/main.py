from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import audio, triage, tasks

app = FastAPI(
    title="S.H.I.E.L.D API",
    description="AI-powered dispatch for Certis security officers",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audio.router)
app.include_router(triage.router)
app.include_router(tasks.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "S.H.I.E.L.D"}
