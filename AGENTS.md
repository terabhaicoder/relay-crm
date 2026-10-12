# ERP project rules

## Working agreement

Read `PLAN.md`, `CHECKLIST.md`, and `CHANGELOG.md` at the start of each session. Run `git status` first; preserve all existing changes. The user's latest instruction supersedes the original ERP phase gates: build and test a usable end-to-end CRM for a hackathon now, without stopping at Phase 0. The original ERP spec and ProcessPay are references, not binding product scope. Continue from the first unchecked active CRM item. Keep future ERP work separate and do not claim it is complete. Do not treat an unverified acceptance check as complete. The user explicitly authorizes multiple agents; give each a non-overlapping file scope and review their combined work.

The rules below preserve useful original engineering guidance. Where stack or infrastructure cannot run locally, choose a documented working alternative (including a real SQLite database for the single-instance hackathon setup); do not simulate persistence or success. Redis/Celery/PostgreSQL are an optional scale path rather than blockers for the CRM. Real auth, tenant isolation, server validation, exact money, honest integration status and working UI interactions remain required.

## Architecture rules — ERP specification Section 3

- Modular monolith, no microservices. Each module owns its tables and exposes a service interface. No module writes another module's tables directly.
- Cross-module side effects use domain events saved in `outbox_events` in the same transaction and processed by Celery with idempotent handlers. See PLAN.md for atomic submission orchestration; no success before all financial and stock effects commit.
- Every business table has `org_id`. Enforce tenancy in ONE base repository layer. Another org's record ID returns 404.
- Hierarchy: Org (tenant) → Company (legal entity, PAN) → Branch (state, GSTIN) → Warehouse.
- Layers: routers → services → repositories → models. No DB calls in routers.
- Standard columns: UUID `id`, `org_id`, `created_at`, `updated_at`, `created_by`, `updated_by`, `deleted_at`. Soft delete masters only. Posted documents are never deleted. PLAN.md explicitly identifies global identity and infrastructure exceptions.
- Money is NUMERIC(18,2), quantity NUMERIC(18,3), rate NUMERIC(18,4). Never float. Server calculations are authoritative; frontend calculations only preview. Rounding differences post to the Round-Off ledger.
- Store UTC; display the user's timezone, default Asia/Kolkata. Financial year is April–March, configurable.
- Indian number formatting (1,00,000 / ₹5.2 L / ₹1.3 Cr), switchable in settings.
- Use DB transactions for every multi-table write, including submit, lead conversion, merge, stock transfer and payroll.
- Require `Idempotency-Key` on create, submit and payment endpoints. Repeated/double-click requests produce one document.
- Use row locks or version checks for stock and document submit. Concurrent sales of the final unit produce one success and one clear failure.
- All filtering, sorting and pagination happen server-side. Never load whole tables in the browser.
- Auto-generated OpenAPI and typed TypeScript client. Frontend types must match backend schemas.

## Honesty rules — ERP specification Section 9

- No mock data or mock APIs in place of a real backend. No dead buttons or links.
- No fake auth/permission checks, empty catch blocks, hardcoded IDs, metrics or records.
- Never show “sent”, “connected”, “synced”, “paid” or “filed” unless confirmed by the provider. For internally settled documents, use the actual posted ledger/allocation state; external payment confirmation requires verified provider evidence.
- Never claim tests passed unless they were run and passed. Record blocked checks and their actual reasons.
- Every schema change requires a new migration. Never edit or delete applied migrations.
- No new dependency without a reason recorded in PLAN.md.
- Demo fixtures must be opt-in, explicitly labelled, idempotent and separate from production. Test doubles may isolate a unit test but are never runtime integrations or evidence of a real integration passing.

## Testing and definition of done — ERP specification Section 15

- Highest coverage: posting, stock, tax, numbering and document engines.
- Include API, tenant isolation, permissions, concurrency, idempotency, import and automation tests, plus Playwright E2E for main journeys.
- A feature is done only when UI, API and DB are complete; validation, permissions and tenant scoping work; all UI states are handled; related modules update correctly; tests have run and passed; CHECKLIST.md is checked; and CHANGELOG.md has an entry.
- Run tests at each phase end and fix failures before moving forward. Retest all applicable acceptance cases below at every phase boundary. Cases awaiting future modules remain explicitly pending, never reported as passed.

### Acceptance checks

- Signup → org → invitation → invited user logs in.
- Own-record visibility enforced in UI and API; another org's record ID returns 404.
- Same-phone duplicate lead warning; convert to contact + customer + deal atomically; second conversion creates nothing new.
- Deal drag records stage history and audit; loss requires a reason; closed deals excluded from open pipeline.
- Import 1,000 rows with 20 invalid → 980 created; downloadable error file.
- Quotation → SO → partial delivery → invoice → part payment → full payment: correct stock valuation, zero closing customer balance, balanced journals, partly/fully delivered and billed statuses.
- Same state CGST + SGST, different state IGST; totals including round-off match hand calculations.
- PO → GRN → bill with differing rate → payment: three-way mismatch flagged, stock and weighted average correct.
- Credit note reverses applicable stock, tax and receivable.
- Invoice cancellation creates reversals, never reuses the number, and remains read-only.
- Double-click Submit creates exactly one invoice.
- Two users sell the last unit: one succeeds, one receives a clear error, stock never becomes negative.
- Posting in a locked period is blocked.
- Seed trial balance balances; P&L profit agrees with movement in balance sheet.
- GSTR-1 totals equal sales register totals.
- Sales Rep cannot see cost price; PO above threshold waits for approval.
- Every dashboard figure matches a direct database query on seed data.
- Tests, lint, type checks and `docker compose up` from a fresh clone all pass.

## Session handoff

Report completed features, key files/architecture, migrations/setup, missing env/credentials, actual test results, known gaps and the next unchecked items. Do not claim the complete ERP is built when only a phase is prepared.
