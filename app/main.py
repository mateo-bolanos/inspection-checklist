from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, Request
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
if "*" in cors_origins:
    logger.warning("CORS_ALLOW_ORIGINS includes '*'; do not use this in production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins, 
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response


@app.on_event("startup")
async def startup_event() -> None:
    if settings.run_migrations_on_startup:
        run_migrations()
    if settings.seed_initial_data:
        if settings.app_profile != "demo":
            logger.warning("Seeding demo data while APP_PROFILE=%s; disable SEED_INITIAL_DATA in production", settings.app_profile)
        seed_initial_data()
    if settings.enable_overdue_monitor:
        _start_overdue_monitor()
    if settings.enable_scheduler_jobs:
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
            try:
                await asyncio.sleep(60)
                with SessionLocal() as db:
                    overdue = count_overdue_actions(db)
                if overdue:
                    logger.info("Overdue issues pending: %s", overdue)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error running overdue monitor loop")

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
            send_friday_pending_reminders,
            send_monday_assignment_kickoff,
        )

        interval = 60 * 60 * 24  # run once per day
        while True:
            try:
                with SessionLocal() as db:
                    created = generate_scheduled_inspections(db)
                    overdue = mark_overdue_scheduled_inspections(db)
                    digests = send_daily_digest_emails(db)
                    reminders = send_day_before_due_reminders(db)
                    monday_notices = send_monday_assignment_kickoff(db)
                    friday_notices = send_friday_pending_reminders(db)
                if created:
                    logger.info("Generated %s scheduled inspections for next week", len(created))
                if overdue:
                    logger.info("Marked %s scheduled inspections as overdue", overdue)
                if digests:
                    logger.info("Sent %s inspection digest emails", digests)
                if reminders:
                    logger.info("Sent %s day-before reminder emails", reminders)
                if monday_notices:
                    logger.info("Sent %s Monday assignment emails", monday_notices)
                if friday_notices:
                    logger.info("Sent %s Friday reminder emails", friday_notices)
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
    return {"status": "ok"}
