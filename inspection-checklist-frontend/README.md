# Inspection Checklist Frontend

A Vite + React + TypeScript SPA for the Safety Inspection Checklist project. The app consumes the FastAPI backend (`mateo-bolanos/inspection-checklist`) exclusively via the generated OpenAPI client.

## Getting Started

```bash
cd inspection-checklist-frontend
cp .env.example .env   # ensure VITE_API_BASE_URL points to FastAPI (default http://localhost:8000)
npm install
npm run generate:api   # requires the FastAPI server running so /openapi.json is reachable
npm run dev            # starts Vite on http://localhost:5173
```

Backend quickstart:

```bash
# in repo root
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Scripts

- `npm run dev` – Vite dev server
- `npm run build` – typecheck + production build
- `npm run preview` – preview production bundle
- `npm run lint` – ESLint over the project
- `npm run test` / `npm run test:watch` – Vitest (unit + component + MSW integration)
- `npm run generate:api` – regenerates `src/api/gen/schema.ts` via `openapi-typescript "$VITE_API_BASE_URL/openapi.json"`

## Testing

Vitest is configured with React Testing Library and MSW. Tests cover:

- auth store + formatting utilities
- Login flow (happy path + invalid credentials)
- Template builder nested form
- Inspection edit guard logic
- Dashboard metrics integration with mocked API

Run `npm run test` locally; the suite uses `jsdom` and requires no backend.

## Project Structure

```
src/
  api/           # axios client, React Query hooks, generated schema
  auth/          # auth store + helpers
  components/    # UI primitives, layout, feedback components
  pages/         # Route pages (Auth, Dashboard, Templates, Inspections, Actions, Reviews, Files)
  routes/        # React Router config and guards
  styles/        # Tailwind entry point
  lib/           # constants, formatters, utilities
  __tests__/     # component + integration tests
```

## Conventions & Notes

- JWT tokens live in memory with a sessionStorage backup. `401` responses clear auth and redirect to `/login`.
- API data is strictly typed via the generated OpenAPI schema. React Query handles caching/invalidation per feature.
- Forms rely on `react-hook-form` + `zod` mirrors of backend DTOs.
- Role-based guards hide unauthorized routes/buttons (`admin` full access, `reviewer` dashboard/reviews, `inspector` inspections/files, `action_owner` limited to the actions workspace).
- Action owners land on `/actions`, only see their assigned items, and can upload evidence/notes without viewing the underlying inspection; admins/reviewers can reassign actions directly from the modal.
- File uploads leverage `/files` via multipart form data with automatic refetches of affected queries.

## Regenerating the Client

1. Start the FastAPI server (`uvicorn app.main:app --reload`).
2. Ensure `.env` points `VITE_API_BASE_URL` to the running backend.
3. Run `npm run generate:api`.

This updates `src/api/gen/schema.ts`, keeping the frontend in sync with backend contracts.
