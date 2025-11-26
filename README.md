# Safety Inspection Checklist

Full-stack reference implementation for managing safety inspections, corrective actions, and evidence collection.  
The repository bundles a FastAPI backend and a Vite/React frontend plus migration/docs tooling.

## Repository Layout

- `app/` – FastAPI application (auth, inspections, actions, dashboard, files)
- `inspection-checklist-frontend/` – React SPA that consumes the API via generated OpenAPI client
- `docs/` – ERD, backlog, and the original project brief
- `alembic/` – Database migrations
- `scripts/` – Utilities (e.g., SQLite → PostgreSQL migrator)

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # define SQLITE_URL/JWT_SECRET as needed
uvicorn app.main:app --reload
```

The server auto-runs Alembic migrations, seeds default users, exposes OpenAPI docs at `http://localhost:8000/docs`, and serves uploaded media from `/uploads`.

Frontend dev server:

```bash
cd inspection-checklist-frontend
cp .env.example .env  # ensure VITE_API_BASE_URL matches FastAPI URL
npm install
npm run generate:api   # pulls the current /openapi.json
npm run dev            # http://localhost:5173
```

### CORS configuration

`CORS_ALLOW_ORIGINS` now accepts comma-, whitespace-, or JSON-array-formatted lists.  
Examples (all equivalent):

- `CORS_ALLOW_ORIGINS=http://localhost:5173,https://app.example.com`
- `CORS_ALLOW_ORIGINS=http://localhost:5173 https://app.example.com`
- `CORS_ALLOW_ORIGINS=["http://localhost:5173","https://app.example.com"]`

The backend normalizes duplicates, strips trailing slashes, and appends `FRONTEND_BASE_URL` automatically so the Vite dev server keeps working out of the box.

## Features

- JWT auth with admin/inspector/reviewer roles and route guards
- Checklist template builder (sections/items)
- Inspection lifecycle (draft → submitted → approved/rejected) with validation rules
- Corrective actions + overdue monitor
- Dashboard metrics + PDF/JSON inspection exports
- Secure evidence uploads with ownership checks

## Testing & Tooling

- Backend tests: `python -m pytest`
- Frontend tests: `npm run test`
- PostgreSQL via `docker compose up postgres` and `USE_POSTGRES=1 alembic upgrade head`

For detailed setup/migration instructions see `docs/README.md`.
