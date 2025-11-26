from __future__ import annotations

import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.migrations import run_migrations
from app.routers import (
    actions,
    assignments,
    auth,
    config as config_router,
    dashboard,
    files,
    inspections,
    locations,
    reports,
    scheduled_inspections,
    templates,
    users,
)
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
async def startup_event() -> None:
    run_migrations()
    seed_initial_data()
    _start_overdue_monitor()
    _start_scheduling_jobs()


@app.on_event("shutdown")
def shutdown_event() -> None:
    _stop_overdue_monitor()
    _stop_scheduling_jobs()


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(templates.router, prefix="/templates", tags=["templates"])
app.include_router(inspections.router, prefix="/inspections", tags=["inspections"])
app.include_router(actions.router, prefix="/actions", tags=["actions"])
app.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
app.include_router(config_router.router, prefix="/config", tags=["config"])
app.include_router(dashboard.router, prefix="/dash", tags=["dashboard"])
app.include_router(files.router, prefix="/files", tags=["files"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(scheduled_inspections.router, tags=["scheduled_inspections"])
app.include_router(locations.router, prefix="/locations", tags=["locations"])
app.include_router(users.router, prefix="/users", tags=["users"])

overdue_task: asyncio.Task | None = None
scheduling_task: asyncio.Task | None = None


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


def _start_scheduling_jobs() -> None:
    global scheduling_task
    if scheduling_task:
        return

    async def _run_daily_scheduling() -> None:
        from app.services.assignments import (
            generate_scheduled_inspections,
            mark_overdue_scheduled_inspections,
            send_daily_digest_emails,
            send_day_before_due_reminders,
        )

        interval = 60 * 60 * 24  # run once per day
        while True:
            try:
                with SessionLocal() as db:
                    created = generate_scheduled_inspections(db)
                    overdue = mark_overdue_scheduled_inspections(db)
                    digests = send_daily_digest_emails(db)
                    reminders = send_day_before_due_reminders(db)
                if created:
                    logger.info("Generated %s scheduled inspections for next week", len(created))
                if overdue:
                    logger.info("Marked %s scheduled inspections as overdue", overdue)
                if digests:
                    logger.info("Sent %s inspection digest emails", digests)
                if reminders:
                    logger.info("Sent %s day-before reminder emails", reminders)
            except Exception:  # noqa: BLE001
                logger.exception("Error running scheduled inspection jobs")
            await asyncio.sleep(interval)

    scheduling_task = asyncio.create_task(_run_daily_scheduling())


def _stop_scheduling_jobs() -> None:
    global scheduling_task
    if scheduling_task:
        scheduling_task.cancel()
        scheduling_task = None


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "database": settings.database_url}
