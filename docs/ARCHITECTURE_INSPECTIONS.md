Documented where inspections, actions, attachments, and dashboards live so the follow-up work can plug into the right layers.

Admin Workflow Diagram

A standalone PNG (`docs/admin-workflow.png`) mirrors the primary admin flow through FastAPI (auth → routers/services → DB/uploads/email) and the background jobs that keep overdue counts and scheduled inspections fresh. Open that file during onboarding or reviews when you need to explain the request/notification path without diving into the code listings below.

User Workflow Diagram

Use `docs/user-workflow.png` when you need to show how an inspector moves from login → drafting → submission, how reviewers approve/reject, and how action owners close the loop with attachments before the inspection is archived. The chart also highlights the decision points (e.g., reviewer send-backs) so process discussions can stay user-focused instead of diving into API layers.

Backend

app/main.py (line 1) instantiates the FastAPI app, wires CORS/static uploads, runs Alembic migrations & data seeding on startup, and starts the overdue-action monitor task (counts open actions every minute).
app/routers/inspections.py (line 27) exposes list/create/update/submit/approve/reject/export endpoints plus response CRUD; PDF export is triggered via the same router in app/routers/inspections.py (line 110).
app/services/inspections.py (line 23) centralizes inspection business logic: template lookups, response creation, submission scoring, and validation hooks (see app/services/inspections.py (line 95) for submission and _validate_submission_requirements at app/services/inspections.py (line 208)).
app/routers/actions.py (line 22) and app/services/actions.py (line 22) own corrective-action CRUD, including assignment (assigned_to_id), status transitions, attachment enforcement before closing, and overdue counts used by the background monitor.
app/routers/files.py (line 17) couples with app/services/files.py (line 22) to upload/list/delete MediaFile entries tied to inspection responses or corrective actions, persisting binaries under /uploads.
app/routers/dashboard.py (line 12) backed by app/services/dashboard.py (line 1) exposes aggregated metrics (overview totals, action severity mix, top failing items) plus a simple HTML preview UI.
Models & Schemas

app/models/entities.py (line 120) defines Inspection with template linkage, location, notes, timestamps, overall_score, and relationships to responses and corrective actions.
app/models/entities.py (line 146) captures InspectionResponse, including result, note, media_files, and helper media_urls used by the API/clients.
app/models/entities.py (line 177) models CorrectiveAction (title, severity, due dates, assigned_to_id, status, started/closed metadata) plus relationships back to inspections/responses and attached media.
app/models/entities.py (line 212) stores MediaFile metadata (file URL, uploader, response/action linkage) representing attachments.
Template structure feeding inspections is described via ChecklistTemplate, TemplateSection, and TemplateItem in app/models/entities.py (line 66), with corresponding Pydantic schemas under app/schemas/template.py and app/schemas/inspection.py (line 1).
Inspection Submission & Validation

Backend submission endpoint lives at app/routers/inspections.py (line 70), delegating to the business rules in app/services/inspections.py (line 95).
_validate_submission_requirements in app/services/inspections.py (line 208) enforces that all required template items have responses and that every failed response has at least one corrective action attached before allowing submission.
Front-end gating mirrors those rules via evaluateInspectionSubmitState in inspection-checklist-frontend/src/pages/Inspections/InspectionEdit.tsx (line 520), which blocks the “Submit inspection” button if requirements/actions are missing.
Attachment handling during submission/editing is wired through inspection-checklist-frontend/src/pages/Inspections/InspectionEdit.tsx (line 204), which uploads files via useUploadMediaMutation before actions can be closed.
Frontend

inspection-checklist-frontend/src/pages/Inspections/NewInspection.tsx (line 1) renders the “Start inspection” form (template/location/notes) and posts via useCreateInspectionMutation.
inspection-checklist-frontend/src/pages/Inspections/InspectionEdit.tsx (line 49) is the main inspection workspace: captures responses, enforces required rules, uploads attachments, spawns corrective actions, and triggers submit/approve mutations.
inspection-checklist-frontend/src/pages/Inspections/InspectionView.tsx (line 1) shows a read-only inspection with responses, media links, and related actions.
inspection-checklist-frontend/src/pages/Inspections/InspectionsList.tsx (line 1) provides the overview/search table with status filtering, quick links to view/edit/actions, and entry to /inspections/new.
Dashboard KPIs and recent inspections are rendered in inspection-checklist-frontend/src/pages/Dashboard/Overview.tsx (line 1), consuming /dash/overview plus inspection/template queries.
Domain Concepts

Locations: Inspection.location in app/models/entities.py (line 123) is editable via both backend updates (app/services/inspections.py (line 81)) and the front-end inputs in inspection-checklist-frontend/src/pages/Inspections/InspectionEdit.tsx (line 306)/NewInspection.tsx (line 16).
Actions/Assignments: CorrectiveAction (app/models/entities.py (line 177)) supports severity, due dates, and assigned_to_id; API logic for creation/update is in app/services/actions.py (line 54), and the UI to create/view them sits inside the inspection editor (inspection-checklist-frontend/src/pages/Inspections/InspectionEdit.tsx (line 252)).
Assignments and action ownership flow through inspectors and managers only (no separate action_owner role). Inspectors can add notes to actions tied to their inspections; only managers (admin/reviewer) can assign/reassign or close actions. Assignees upload/download attachments for actions they own, and the actions workspace defaults to “My actions” for non-managers.
Scheduling: there is no dedicated scheduling module, but due dates plus the overdue monitor in app/main.py (line 61)/app/services/actions.py (line 139) log overdue corrective actions.
PDF reports: supported via app/services/reports.py (line 10) with PDF rendering handled by FPDF, exposed through the /inspections/{id}/export?format=pdf route at app/routers/inspections.py (line 110).
Email utilities: app/services/email.py wraps SMTP using SMTP_* env vars declared in app/core/config.py/.env.example. HTML templates live under app/templates/email/.

Notifications: assignment generation (app/services/assignments.py) emails the assignee when a ScheduledInspection is created; app/main.py's daily scheduler also triggers assignment digests plus day-before reminders via app/services/assignments.py. Successful submissions send inspection_submitted.html via background tasks in app/routers/inspections.py -> app/services/inspections.py.
