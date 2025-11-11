from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.migrations import run_migrations
from app.routers import actions, auth, dashboard, files, inspections, templates
from app.seeds.seed_data import seed_initial_data

logger = logging.getLogger("inspection_app")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Safety Inspection Checklist API", version="0.1.0")

cors_origins = settings.cors_allow_origins or ["*"]
allow_credentials = "*" not in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    run_migrations()
    seed_initial_data()
    _start_overdue_monitor()


@app.on_event("shutdown")
def shutdown_event() -> None:
    _stop_overdue_monitor()


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(templates.router, prefix="/templates", tags=["templates"])
app.include_router(inspections.router, prefix="/inspections", tags=["inspections"])
app.include_router(actions.router, prefix="/actions", tags=["actions"])
app.include_router(dashboard.router, prefix="/dash", tags=["dashboard"])
app.include_router(files.router, prefix="/files", tags=["files"])

UPLOADS_PATH = Path("uploads")
UPLOADS_PATH.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_PATH)), name="uploads")

overdue_task: asyncio.Task | None = None


def _start_overdue_monitor() -> None:
    global overdue_task
    if overdue_task:
        return

    async def _monitor() -> None:
        from app.services.actions import count_overdue_actions

        while True:
            await asyncio.sleep(60)
            with SessionLocal() as db:
                overdue = count_overdue_actions(db)
            if overdue:
                logger.info("Overdue corrective actions pending: %s", overdue)

    overdue_task = asyncio.create_task(_monitor())


def _stop_overdue_monitor() -> None:
    global overdue_task
    if overdue_task:
        overdue_task.cancel()
        overdue_task = None


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "database": settings.database_url}
