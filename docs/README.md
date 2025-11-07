# Safety Inspection Checklist

## Setup
1. Create and activate a Python 3.11+ environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and update secrets as needed.
4. Run the initial database migration and seed data:
   ```bash
   uvicorn app.main:app --reload
   ```
   The application auto-runs Alembic and seeds default admin (`adminpass`), reviewer (`reviewerpass`), and inspector (`inspectorpass`).

## Local Development
- **API server**: `uvicorn app.main:app --reload`
- **Authentication**: obtain a token via `/auth/login` using seeded credentials.
- **Docs**: visit `http://localhost:8000/docs` for the OpenAPI explorer.
- **Tests**: run `python -m pytest` (uses an isolated SQLite test database).

## Media & Reports
- Upload evidence with `POST /files/` (`response_id` or `action_id` required).
- Dashboard metrics live at `/dash/*` and `/dash/ui` (paste a JWT token to preview data inside the simple HTML shell).
- Export inspection summaries with `GET /inspections/{id}/export?format=json|pdf`.

## PostgreSQL Migration
1. Start PostgreSQL locally:
   ```bash
   docker compose up -d postgres
   ```
2. Set `POSTGRES_URL` (e.g. `postgresql+psycopg://inspection:inspection@localhost:5432/inspection`) and run:
   ```bash
   USE_POSTGRES=1 POSTGRES_URL=... alembic upgrade head
   ```
3. To migrate existing SQLite data:
   ```bash
   USE_POSTGRES=1 POSTGRES_URL=... python scripts/migrate_sqlite_to_postgres.py
   ```
4. Boot the API against PostgreSQL:
   ```bash
   USE_POSTGRES=1 POSTGRES_URL=... uvicorn app.main:app --reload
   ```
5. Stop services when done: `docker compose down`.

## Deployment
A simple `Dockerfile` is included. Build and run with PostgreSQL connection details provided via environment variables:
```bash
docker build -t inspection-api .
docker run -p 8000:8000 --env-file .env inspection-api
```
