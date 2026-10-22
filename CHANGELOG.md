# Changelog

## 2026-10-22 — Public source preparation

- Prepared the connected CRM implementation, migrations 0006–0010, generated contracts and tests for public `main` publication.
- Excluded local presentation output and additional SQLite sidecar formats; retained existing environment, database, upload, backup and build exclusions. Removed machine-specific documentation paths and corrected current feature/roadmap descriptions.
- Marked the saved-view UI journey as skipped because its control was intentionally removed; retained its active backend/API coverage.
- Release validation: 215 backend tests passed, one optional integration test deselected; seven backup tests and five proxy tests passed; Ruff/format (94 files), mypy (69 sources), frontend lint/types, generated-contract consistency and production build passed. Production npm audit reported zero vulnerabilities. Two upstream Python deprecation warnings remain. No automated E2E, Docker or deployment run.

## 2026-10-22 — Relay hackathon PowerPoint

- Created an eight-slide editable PowerPoint with Relay branding, six actual Chrome product screenshots, concise connected-workflow story and credits for Paarth Panthri and Nishanth KS.
- Clearly distinguished fictional demo records, working local features and future connectors; added presenter notes for quotation, forecast and communications boundaries.
- Delivered `outputs/relay-hackathon.pptx` and a Downloads copy. These presentation files are local deliverables, not included in the source repository.
- Rendered and visually reviewed every slide; verified eight slides/notes, editable objects, valid archive, correct credits and no bounds/content-overlap violations. Corrected the preview's year, logo filter and contrast. No new app dependency, migration, Docker or automated E2E run.
- Updated the demo guide to reflect implemented local capture and removal of saved-view controls.

## 2026-10-22 — Cleaner lists for the hackathon deck

Removed the full-width Saved views / Current filters / Save current view bar from CRM lists at the user’s request. Search, filters, sorting and pipeline controls remain. The saved-view API and existing stored presets are preserved, but their previous list UI is no longer exposed. Frontend lint/types passed; Chrome confirmed no bar on Pipeline and fresh screenshots use the cleaned UI. No migration or dependency change.


## 2026-10-22 — Local capture, durable workflows and custom fields

- Added manager-configured public local lead forms, consent/validation, duplicate-safe receipt storage, round-robin routing and real inquiry counters/navigation. Capture calls the CRM service, so audit and automation effects commit with the new lead. Migration 0010.
- Added durable ordered automation steps for tasks, in-app notifications and owner assignment; delays, current permission/condition rechecks, immutable snapshots, pause cancellation, retry/cancel, linked history and API-owned local worker. Migration 0008; no external queue dependency.
- Added typed optional custom fields on leads/contacts/companies/deals/tickets, versioned saves, archive/restore and audit history. Compatible values follow conversion and fill unset values during merge; intake and automation links also follow merges. Migration 0009.
- Integrated dedicated workflow workspace, custom-field settings/drawers, local capture page and honest planned connector catalog. Fixed inherited checkbox sizing, intake refresh/retry states and custom lead-source display. Preserved Relay's existing visual system and favicon.
- Combined backend: 211 passed, one optional test deselected, two upstream warnings. Final targeted intake/workflow: 23 passed; customization: 20 passed; existing CRM regression: 44 passed. Ruff/format and mypy 69 sources passed. Final frontend lint/types, five proxy tests and production build passed.
- Manually verified in Chrome: form → lead/owner → immediate task → one-minute delayed notification; custom lead field → converted contact; duplicate inquiry after conversion → two receipts/one lead. Desktop form and execution-history screenshots reviewed. No automated E2E, Docker, external sends or deployment work.
- Restart the local API for 0008–0010 and the worker. No new dependency, environment secret or connector credentials required. External connectors remain explicitly deferred; support intake/SLA, catalog, shared views and deeper reporting remain future scope, not complete ERP claims.


## 2026-10-22 — Connected sales workflow, forecast and private views

### Delivered

- Benchmarked major workflows against official commercial CRM documentation and open-source projects; capability matrix, source links and remaining gaps are in `docs/CRM_AUDIT_2026-10-22.md`.
- Added the commercial module and migration `0006_quotations.sql`: deal-linked quotation drafts, exact Decimal line/discount totals, customer snapshots, locked issued terms, recorded decisions, printable documents and optional atomic acceptance-to-won. Decision evidence is entered by the user; no delivery, electronic signature, invoice, tax or payment is claimed.
- Added a close-date sales forecast with weighted/open/won/lost values, monthly totals, pipeline/date filters, owner filtering in the UI and API, paginated drill-through and overdue/undated attention lists. Open-stage probability changes now update affected open deals and their versions without changing closed outcomes.
- Added the views module and migration `0007_saved_views.sql`: private, validated search/status/sort presets with save/apply/update/delete; deal views retain pipeline and board/table mode.
- Connected record-to-email creation, recipient prefill, template application, paginated linked drafts and reopen/edit with preserved relationships. Email remains an unsent preparation workflow; adding credentials alone does not implement a mailbox adapter.
- Exposed all eleven supported automation events with compatible condition fields. Fixed assigned-record workflow updates while retaining private customer access controls, and native browser date values being replaced during React updates.
- Integrated quotation/deal actions, forecasting, saved views and the Relay tab icon (`frontend/src/app/icon.svg`) while preserving the existing design and prior stylesheet edits. Updated generated API contracts. No applied migration was changed and no new runtime dependency was introduced.

### Actual verification and current scope

- Final backend suite: **172 passed, one optional test deselected**. Mypy: **56 source files passed**. Final frontend ESLint, TypeScript, **five proxy tests** and isolated production build passed; the earlier **nine frontend unit tests** also passed.
- Before the latest instruction, targeted automated browser checks ran and the combined suite was attempted. **The combined run was stopped at the user's request; no complete-suite pass is claimed. No further automated E2E runs are authorized in this session.**
- Current review is **local only, manual Chrome**. Verified signup → lead → linked contact/company/deal conversion → quotation create/issue/record acceptance with deal won → forecast showing **₹1,25,000.50**. Also verified company overview → pre-linked dated task → correct My Day and Calendar entries.
- Further manual Chrome review verified contacts search “Mira” → private “Northstar contacts” view save → reload/apply; contact → prefilled email draft → save/reopen retaining the contact → create/apply template with name/company/email resolving to Mira Audit / Fictional Northstar Labs / mira.audit@example.test → save. The draft remains unsent.
- Manual support review created a company-linked ticket, added an internal note and saved Resolved; the list retained that status.
- Manual campaign review created a campaign with ₹5,000.50 budget, searched/added the existing converted Mira lead and observed one member, 1/1 converted and 100%. Removing membership returned the count to zero; the Leads list confirmed Mira remained unchanged. This is pre-converted-member tracking, not evidence of in-campaign conversion or revenue attribution.
- Manual automation review created a leads.created rule with a one-day task, created Sam Fictional Inquiry and found “Review new customer inquiry” due 2026-10-23 in My Tasks. Opening it confirmed the Sam lead link and automation note; completing it persisted completed status in the list. Other triggers, condition branches and notification actions were not covered by this manual path.
- Manual Chrome also verified updating the saved filter/name and deleting the disposable view with success confirmation. Historical checks elsewhere describe their own snapshots; this bounded review does not claim exhaustive browser/accessibility coverage.
- Docker, remote deployment, TLS and production release certification are outside the active task. Earlier deployment checkboxes remain historical and unchecked. No complete ERP claim is made.

### Local setup and remaining work

Restart the local API to apply migrations 0006/0007 and load the added routes. No new environment variables or external provider credentials are required for these local workflows. The bounded manual Chrome review is complete; CHECKLIST.md distinguishes its verified paths from historical and future scope. Major remaining product gaps include public intake/routing, real communications, support intake/SLA, custom fields/shared views/bulk actions, scheduled multi-step automation and deeper forecasting/integrations.


## 2026-10-22 — Related-record field spacing

- Fixed the search input touching the “None” dropdown: the former spacing rule targeted a hidden native select. The relation field now uses an 8px grid gap and consistent input sizing; existing search, selection and clearing behavior is unchanged.
- Frontend lint and TypeScript checks passed. Design hook found no deterministic stylesheet issues; live visual verification was not performed, following the user's request to change code only. No dependencies, migrations or credentials needed.

## 2026-10-12 — Connected CRM coverage for the hackathon

### Implemented

- User prioritized complete sales/support workflows over additional granular role work. Existing auth, tenant isolation and backend checks were preserved; no new role-matrix expansion, external sends or Gmail integration is claimed.
- Company/contact Customer overview now joins real customer relationships, deal/support totals, paginated records and audit history, with pre-linked follow-up/deal/ticket actions.
- Campaign membership now persists lead/contact links with duplicate prevention, scoped list/remove and real converted-lead metrics. Added append-only migration `backend/local_migrations/0005_campaign_members.sql`; removal keeps the original CRM record. Metrics do not claim attributed revenue or ROI.
- My Day adds server-counted overdue/today/upcoming tasks, lead follow-ups, stalled deals and support queues, with scope controls, pagination and task completion.
- Pipeline settings adds editable sales processes, ordered stages and win probability. Existing outcomes/history are protected. Pipeline boards use full server totals and independent stage pagination, preserving loss reasons and concurrency checks.
- Calendar now loads complete counts for its 42 displayed dates and paginates the selected-day agenda. Search/status apply consistently, date-only values keep their day and timestamped values group in IST.
- Independent review fixed empty-status calendar filtering, summary/agenda filter disagreement, stale agenda pages after filtering, closed-stage creation and an obsolete board test selector. Four real-server browser journeys cover the new connected flows.
- Existing shared editor, API client and custom Select are reused. New components use scoped CSS; no new runtime dependency was added. Prior migrations and future ERP scope were preserved.

### Tests and live evidence

- Backend: **136 passed**, one optional PostgreSQL check deselected, one upstream warning. Ruff/format passed for 56 files; mypy passed for 42 sources.
- Frontend: lint, TypeScript and **9 unit tests passed**. Isolated production build passed before the final narrow pipeline-editor adjustment; subsequent lint/types passed for that change without overwriting the live development output.
- Playwright discovery: **19 tests in 5 files**, including four new coverage journeys. Automated browser execution is still blocked by the missing Chromium runtime; discovery is not a passing browser run.
- Following the user's server restart, live Chrome verified My Day counts and Due today plus disposable signup → ₹45,000.50 lead → conversion → company list. Remaining customer overview, campaign, pipeline and calendar browser flows are still being checked and are not marked passed here.
- Current evidence and remaining acceptance are tracked in `artifacts/crm-coverage/ACCEPTANCE.md`. Earlier audit reports describe their own snapshots; this entry supersedes their campaign-membership and complete-calendar implementation gaps, not their outstanding release gates.

### Setup and remaining gaps

- Apply the new numbered local migration using the existing application migration/startup path; the user has restarted the local app for current verification. No new environment variables or credentials are required for these CRM additions.
- New-feature browser acceptance, all 19 automated journeys, exhaustive responsive/accessibility checks and fresh-container/TLS/restore verification remain pending. Saved views/custom fields, recurring reminders, advanced SLA/forecasting and live communication channels remain outside this pass. No complete ERP or production-certified claim is made.

### Final verification follow-up

- Fixed a live React sibling-key collision between contextual new-record editors and AutoCreate. Fresh Chrome verification showed one correctly linked task drawer and zero after closing. Added repeated-route and duplicate-key assertions to the authored browser test.
- Calendar day selection/search, customer totals/related deals, pipeline board/settings and campaign member search were inspected live. No mutations were made to the user's existing records; only disposable QA records were created and removed.
- Removed unsupported generic sort/status controls from calendar/board. Selected-pipeline exports now agree across UI/API; returning to Board clears hidden table filters. Final export change passed 14 workspace and four existing import/export tests, Ruff and strict mypy. Regenerated API contracts. One more backend restart is needed for this final export patch.
- Final isolated production build passed after every source change. Pending task actions say Complete and due dates use IST-aware labels. Frontend lint/type checks passed after final changes.
- Live migration 0005 confirmed. QA tenant removed transactionally; other tenant counts unchanged and foreign keys pass. Chrome recovered and was finalized with My Day open. Full new mutation workflows, 19 automated journeys and deployment gates remain unchecked; see current acceptance artifact.
- Bounded screenshot review retains a minor board scrolling-discoverability issue. Calendar full-page capture artifacts and a loading-only settings screenshot limit visual evidence; no mobile acceptance claimed. Existing typography retained with no new suppressions.

## 2026-10-12 — Post-restart live verification

- User restarted the application. Fresh disposable Chrome signup/import confirmed live persistence: 1,000 input rows produced 980 leads and 20 errors.
- Actual Chrome CSV downloads now verified after restart: 980 unfiltered rows and 1 searched row, exact name/email sets, descending order, Unicode, multiline text, ₹123.45 values and formula-safe Indian phone numbers. This confirms the repaired empty-status export behavior is active.
- Reimporting the actual downloaded export produced 0 created / 980 skipped / 0 errors. A malformed file with a valid first row was rejected before any record was written; direct SQLite checks remained at 980 rows.
- QA owner signed out; temporary organization, user and all records removed transactionally. Other-tenant counts unchanged and foreign keys passed. Evidence: `artifacts/crm-audit/restart-export-evidence.json`, downloaded CSV copies, `restart-verification.png`, and `restart-cleanup.json`.
- No application code changes or additional server restart. Automated browser/mobile and other previously documented gaps remain; this targeted check does not rerun the entire audit.

## 2026-10-12 — End-to-end CRM audit, live verification and repairs

### Fixed

- Parallel agents repaired UI/navigation, CRM/API integrity and CSV portability with separate file ownership; an independent reviewer checked combined work. Root owned Chrome. Existing workspace is not a Git repository and all prior files were preserved.
- CSV exports no longer become empty when the UI sends an empty status filter. Exports respect sort/search/tenant/owner and include every matching page. Strict malformed-file/header validation, row-shape errors, ambiguous duplicate update rejection, semicolon-safe JSON tags and formula/apostrophe roundtrips prevent silent data corruption.
- CRM validation prevents ticket/contact/deal company mismatches and invalidating existing relationships; sales representatives cannot clear ownership to bypass own-record rules. Automation-generated follow-ups keep valid customer context; existing invalid task chains repair safely on edit/completion.
- Attachment retries now honor supplied idempotency keys, including concurrent retries, changed-payload conflicts, current-access checks and real disk cleanup. Automation, email draft/template and pipeline creates now also honor supplied keys. Keys remain optional for compatibility; universal required-key enforcement remains incomplete.
- Automation and email-draft lists now implement real server search/sort/pagination/totals. UI labels use creation dates because these records lack update timestamps.
- Frontend fixes cover stale relationship results, actual assignment, clearing optional links, read-only board actions, exact-record dashboard links, invitation-state isolation, logout routing, notification and attachment loading/error/retry, stable support-note/upload retry keys, honest email draft actions, paise formatting and actual-owner avatars.
- Live testing exposed dates displayed by native inputs being omitted at save. Forms now read named date fields at submit; persisted date was verified directly in SQLite and after reload. UTC timestamps display explicit Asia/Kolkata/IST; date-only fields stay unchanged. Unchanged date controls preserve existing full timestamps, and template creation retains stable retry keys after failed requests; both have direct regression tests.
- Added `NEXT_DIST_DIR` support and isolated Playwright build directories so production/test outputs do not overwrite the live `.next` directory. No database migration or runtime dependency added.

### Live evidence and tests actually run

- Chrome signup → owner login → private invitation → Read-only acceptance/login/refresh/logout passed with fictional accounts on a separate localhost origin. Original127.0.0.1 user credentials/roles/session were preserved; no external invitations or messages were sent.
- Actual CSV UI upload:1,000 rows with20 invalid →980 created and20 errors. Database confirmed980 leads +980 audit entries. Retry:0 created /980 skipped /20 errors. Downloaded error file parsed to exactly20 invalid rows. Unicode, Indian numbers, quoted commas, multiline notes and₹123.45 survived persistence.
- Live lead Source keyboard selection/edit → conversion into1 linked company/contact/deal → loss reason; task completion/date reload; support high priority/internal note/customer reply draft; read-only creation controls; landing keyboard workflow tab and Gmail FAQ verified. Desktop screenshots and direct database evidence are in `artifacts/crm-audit`.
- Final test counts and command logs are recorded in `artifacts/crm-audit/ACCEPTANCE.md` and adjacent logs. Frontend9 unit tests (5 proxy + currency + timezone + date preservation + retry keys), lint/typecheck and isolated production build passed; backup/restore7 tests passed. Backend combined suite: **123 passed**,1 optional PostgreSQL check deselected, with one upstream multipart warning. Ruff/format54 files, mypy40 sources and generated-contract drift passed.
- QA organization and all its records/two users were removed in one transaction after verification. Foreign-key check passed, and every other tenant's table counts stayed unchanged; see `cleanup.json`.

### Explicitly unverified or incomplete

- Ten automated browser tests stopped before assertions because Chromium1243 is missing; attempted install failed DNS. Fifteen tests are now authored/discovered; new tests remain unrun. Chrome manual results are separate from automated acceptance.
- Responsive override390×844 did not change the actual1792×976 Chrome viewport; no new mobile/tablet pass claimed. Exhaustive navigation, drag gestures, cross-tenant UI races and all keyboard/error-state permutations remain pending.
- The initial audit could not verify the repaired browser export until restart. This blocker was resolved by the subsequent user restart and live verification recorded above.
- Docker configuration parses; Docker socket access is denied. Fresh-container/TLS/host restore and dependency advisory clearance remain deployment gates. Gmail/sending is deferred. Campaign memberships, advanced support permissions/SLA, full calendar datasets and per-user timezone preferences are not implemented.
- The acceptance matrix records PASS/FAIL/BLOCKED/NOT IMPLEMENTED by evidence and scope; this is not a complete ERP or deployment-ready claim.

## 2026-10-12 — Landing page, custom dropdowns and navigation repair

- Built the public Relay landing at `/`, with responsive navigation, interactive sales-to-support journey, FAQs and working `/dashboard` entry links. Preserved the established visual system; no invented metrics or provider claims.
- Fixed whole-workspace remounting and false empty-state flashes on sidebar navigation. Scoped list/detail/search requests ignore stale responses; retries show loading and record URL changes clear old details.
- Replaced all visible native dropdowns with one custom keyboard-operated component. Real form values, validation, disabled states, reset, viewport placement and drawer Escape behavior are preserved.
- Corrected report currency/percentage formatting, removed internal metadata labels, enabled actual record drill-through and labelled the icon-only mobile search control.
- Live Chrome checks visited all 13 sidebar destinations; verified populated list transitions, dropdown keyboard/mouse use, 390px drawer placement, global search/deep link, landing tabs/FAQ/mobile navigation. Created and reopened one disposable QA lead to verify Referral/Qualified values persisted to the API, then deleted it; original nine leads remain.
- Desktop/mobile screenshots saved under `artifacts/ui-review`; independent review found one journey-panel focus issue, fixed. Landing document width equals its 390px viewport. Detector returned two Arial font findings retained for design consistency, not ignored as a clean scan.
- Final frontend ESLint, TypeScript and isolated standalone production build passed. Five proxy tests passed. Ten Playwright tests are discovered; the attempted seven-test run stopped before assertions because Chromium headless-shell revision 1243 is missing. Full automated journeys remain unchecked.
- No database migrations, new dependencies or credentials needed for these changes. User-started local server was preserved; no remote deployment or external messages. Next: install the browser runtime and run all ten journeys, then complete fresh-container/TLS/restore and dependency-advisory release gates.

## 2026-10-12 — CRM deployment hardening

### Implemented

- Parallel backend, CRM and frontend audits plus independent static review. Preserved existing files; workspace remains outside Git.
- Working invitation creation/acceptance UI, expired-link handling, team role changes, deactivation/reactivation, active session revocation and production signup visibility.
- Fixed cross-account stale UI data by clearing tenant state and invalidating pending requests on authentication changes. Backend session timestamps now include UTC offsets.
- Corrected CRM relationship validation/deletion, existing-contact conversion links, current-owner audit/cache visibility, date normalization, repeated close/resolve timestamps, support-note idempotency, default-pipeline concurrency and import rollback boundaries.
- SQLite-safe monetary input maximum and Decimal dashboard aggregates; no floating SQL sum used for monetary totals.
- Production HTTPS origin checks, disabled public signup option, private interactive owner bootstrap and audited password recovery with session revocation. Stronger scrypt hashes retain backwards compatibility and upgrade on successful login.
- Bounded request bodies in both API/proxy, bounded account/IP throttling, private response headers, automation visibility fixes and longer bounded synchronous-import timeout.
- Standalone production Compose plus Caddy HTTPS gateway, private API network, persistent data/certificate volumes, app health checks, reduced app privileges and rotating logs.
- Backup/verify/restore tooling validates database integrity, foreign keys, file size/content hashes and refuses existing restore destinations. Added deployment/recovery/rollback runbook and real HTTP staging smoke script.
- CI now includes generated-contract drift, proxy tests, dependency advisory checks, container startup, HTTP smoke and browser journeys against built containers. CI was authored, not observed running.

### Validation actually run

- Backend combined suite: **79 passed, 1 optional PostgreSQL check deselected**, with one upstream Starlette multipart deprecation warning. After an annotation-only cleanup, the targeted security suite also passed **11 tests**.
- Backend Ruff and formatting: passed (**54 files**); strict mypy: passed (**40 source files**).
- Backup/restore tests: **7 passed**, including exact-byte recovery, tamper detection, missing files, traversal rejection and overwrite protection. Root operational scripts pass Ruff/format checks.
- Frontend TypeScript, ESLint and Next production build: passed, including the new invitation route. Proxy unit tests: **5 passed**; these deliberately isolate upstream transport and are not live integration evidence.
- Staging smoke assertions passed against the real API and temporary SQLite in-process as part of the backend suite. Actual HTTP through a running Next server remains pending.
- Generated OpenAPI/TypeScript regeneration and drift check passed. Development and production Compose configuration validation passed. CI YAML parsed successfully.
- Independent static review found tenant-cache and timezone defects; both were fixed and passed bounded static confirmation. No browser/visual acceptance is implied.

### Migrations, setup and remaining release gates

- **No new database migrations or runtime Python/npm dependencies.** Existing numbered migrations remain unchanged. The added Caddy infrastructure dependency and SQLite monetary limit are documented in PLAN.md.
- Production requires a Linux/Docker host, DOMAIN and TLS_EMAIL, DNS and inbound 80/443. Keep SIGNUP_ENABLED=false and create the first owner with the private CLI. No Gmail credentials are required for the implemented draft workflows.
- Native startup and isolated Playwright startup were retried: API initialized, but localhost ports failed with EPERM. No browser journey ran. Docker socket access remains denied; fresh-container startup, TLS issuance and deployment restore drills remain unchecked.
- npm production dependency audit was attempted and failed because registry.npmjs.org could not resolve. Dependency security clearance is therefore pending, not passed.
- Gmail sending/sync, email password reset, advanced support SLA/escalations, saved views/custom fields, background import jobs and multi-instance scale remain outside the implemented release. Operator password recovery is available; it is not an email integration.
- No remote deployment, external communication or change to real customer data was performed. The next active checklist items are browser/visual acceptance, fresh-container/TLS/restore acceptance and connected dependency checks.

## 2026-10-09 — Relay CRM implementation

The user changed the active goal from a Phase 0 ERP plan to a usable end-to-end **B2B sales plus customer-support CRM**. The original ERP roadmap remains in PLAN.md and CHECKLIST.md as future scope. Gmail connection was explicitly deferred.

### Delivered code

- Real FastAPI/SQLAlchemy backend with persistent SQLite, safe error responses, structured logging and OpenAPI documentation.
- Organization signup, password hashing, httpOnly cookie sessions, login/logout, password changes, session revocation, team management, member deactivation, invitation tokens, origin checks and authentication rate limiting.
- Tenant- and owner-scoped leads, contacts, companies, pipelines, stages, deals, tasks/calls/meetings/notes, campaigns and support tickets.
- Atomic repeat-safe lead conversion and duplicate-lead merging that preserves activities, attachments, drafts and history; stage history and audit; mandatory loss reason; closed-deal exclusion from open pipeline; stale-version checks and idempotent create operations.
- CSV imports with independent row validation/savepoints/deduplication and downloadable error content; scoped CSV exports with spreadsheet-formula protection.
- Full-database dashboard aggregates, creation-cohort period filtering, global search, timelines, support internal notes and clearly identified unsent reply drafts.
- Conditional automation producing persisted tasks and notifications, per-event deduplication, execution logs, pause/resume, notification read state, email templates and drafts.
- Private record attachments with authenticated binary upload/download/delete, file-type checks, 10 MB limits and transactional merge retention.
- Responsive Next.js interface connected to the real APIs, same-origin cookie proxy, generated API contracts, sample-data onboarding and empty states.
- Explicit opt-in idempotent fictional demo records; no default production administrator or embedded provider credential.
- One-command native launcher, two-service Docker definition, CI workflow, reproducible frontend lock and tested Python runtime dependency snapshot.

### Migrations

- `backend/local_migrations/0001_auth.sql`: organizations, users, sessions, invitations and auth security events.
- `backend/local_migrations/0002_crm.sql`: CRM records, histories and idempotency records.
- `backend/local_migrations/0003_engagement.sql`: automation rules/runs, notifications, templates and email drafts.
- `backend/local_migrations/0004_attachments.sql`: private attachment metadata and record links.
- Startup records checksums and refuses altered applied migrations. Real database tests cover schema/model parity and repeat application.
- The retained Alembic extension migration is future PostgreSQL infrastructure, not applied or validated in this runtime.

### Verification actually completed

- Backend combined suite: **56 passed, 1 PostgreSQL-only check deselected**. Tests use the actual API and temporary SQLite databases, including tenant/owner isolation, permissions, auth, migration tampering, transactional conversion rollback/replay, simultaneous idempotent creation, automation deduplication, ticket workflow and 1,000-row import with exactly 980 accepted rows.
- Backend Ruff checks and formatting: **passed, 49 files checked for formatting**.
- Backend strict mypy: **passed, 37 source files**.
- Frontend TypeScript, ESLint and Next.js production build: **passed after the final changes**. Independent static review findings were fixed, including linked-record navigation, draft/converted states, import error downloads and topmost-dialog keyboard handling. The attachment proxy preserves binary content and private-download headers.
- OpenAPI export and TypeScript regeneration/drift check: passed.
- Docker Compose configuration validation and environment bootstrap preservation: passed.
- Invalid numeric automation comparisons are rejected before enabling a rule.
- One pre-existing Starlette multipart deprecation warning remains in the backend test output.

### Verification limits and remaining work

- Native startup was attempted with `python3 scripts/dev.py`. Both servers initialized but binding localhost ports 3007/8010 failed with `EPERM`. Broader-permission execution was automatically rejected by the session's approval policy. No working preview is claimed.
- Browser navigation confirmed connection refused. Playwright journey execution, screenshots, responsive visual review and keyboard interaction verification remain pending; authored browser tests are not counted as passed.
- Docker socket access is denied; images and fresh-container startup are unverified. The CI workflow is authored, not an observed successful CI run.
- Gmail OAuth/sync/send, password-reset email, advanced granular permissions, saved views/custom fields, advanced support SLA/escalations, background jobs and production scaling remain future work. Email and support replies are drafts today.
- Imports are synchronous and bounded. Role rules are intentionally narrower than the original ERP matrix. Each identity belongs to one organization. SQLite is a single-instance deployment profile, not a production scale certification.
- Initial directory was empty and not a Git repository. No existing application, customer data or uncommitted user code was replaced. No Git commit, push or remote deployment was performed.
