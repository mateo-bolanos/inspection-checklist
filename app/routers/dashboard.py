from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dashboard import ActionMetrics, ItemsMetrics, OverviewMetrics
from app.services import auth as auth_service
from app.services import dashboard as dashboard_service

router = APIRouter()


@router.get("/overview", response_model=OverviewMetrics)
def read_overview(
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.get_current_active_user),
) -> OverviewMetrics:
    return dashboard_service.get_overview_metrics(db)


@router.get("/actions", response_model=ActionMetrics)
def read_action_metrics(
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.get_current_active_user),
) -> ActionMetrics:
    return dashboard_service.get_action_metrics(db)


@router.get("/items", response_model=ItemsMetrics)
def read_item_metrics(
    limit: int = 5,
    db: Session = Depends(get_db),
    _: object = Depends(auth_service.get_current_active_user),
) -> ItemsMetrics:
    return dashboard_service.get_item_failure_metrics(db, limit=limit)


@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def dashboard_ui() -> HTMLResponse:
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <title>Safety Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 2rem; background: #f8fafc; }
            header { margin-bottom: 1.5rem; }
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }
            .card { background: white; border-radius: 8px; padding: 1rem; box-shadow: 0 2px 6px rgba(15,23,42,0.1); }
            label { display: block; margin-bottom: 0.5rem; font-weight: bold; }
            input { padding: 0.5rem; width: 320px; max-width: 100%; }
            button { padding: 0.5rem 1rem; margin-left: 0.5rem; }
            pre { white-space: pre-wrap; word-break: break-word; }
        </style>
    </head>
    <body>
        <header>
            <h1>Safety Inspection Dashboard</h1>
            <p>Paste a valid JWT token to preview live metrics from the API.</p>
            <label for="tokenInput">Bearer token</label>
            <input id="tokenInput" type="text" placeholder="ey..." />
            <button onclick="loadMetrics()">Load Metrics</button>
        </header>
        <section class="metrics">
            <div class="card">
                <h2>Overview</h2>
                <pre id="overview">Awaiting data...</pre>
            </div>
            <div class="card">
                <h2>Actions</h2>
                <pre id="actions">Awaiting data...</pre>
            </div>
            <div class="card">
                <h2>Item Failures</h2>
                <pre id="items">Awaiting data...</pre>
            </div>
        </section>
        <script>
            async function loadMetrics() {
                const token = document.getElementById('tokenInput').value.trim();
                if (!token) { alert('Enter a token first.'); return; }
                const headers = { 'Authorization': `Bearer ${token}` };
                const endpoints = {
                    overview: '/dash/overview',
                    actions: '/dash/actions',
                    items: '/dash/items'
                };
                for (const [target, url] of Object.entries(endpoints)) {
                    const el = document.getElementById(target);
                    el.textContent = 'Loading...';
                    try {
                        const res = await fetch(url, { headers });
                        if (!res.ok) throw new Error(await res.text());
                        const data = await res.json();
                        el.textContent = JSON.stringify(data, null, 2);
                    } catch (err) {
                        el.textContent = `Error: ${err}`;
                    }
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
