from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.app.routers import chat, files, jobs, projects
from reposage.config import get_settings
from reposage.logging import configure_logging
from reposage.schemas import HealthRead

configure_logging()
settings = get_settings()

app = FastAPI(title="RepoSage API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(projects.router)
app.include_router(files.router)
app.include_router(chat.router)
app.include_router(jobs.router)


@app.get("/health", response_model=HealthRead)
def health() -> HealthRead:
    return HealthRead(status="ok")

