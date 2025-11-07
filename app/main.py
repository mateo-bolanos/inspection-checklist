from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.migrations import run_migrations
from app.routers import actions, auth, dashboard, files, inspections, templates
from app.seeds.seed_data import seed_initial_data

app = FastAPI(title="Safety Inspection Checklist API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    run_migrations()
    seed_initial_data()


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(templates.router, prefix="/templates", tags=["templates"])
app.include_router(inspections.router, prefix="/inspections", tags=["inspections"])
app.include_router(actions.router, prefix="/actions", tags=["actions"])
app.include_router(dashboard.router, prefix="/dash", tags=["dashboard"])
app.include_router(files.router, prefix="/files", tags=["files"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "database": settings.database_url}
