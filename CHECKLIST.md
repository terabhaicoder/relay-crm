# Relay CRM delivery checklist — current request

## Public source preparation — 2026-10-22

- [x] Review candidate source/docs for embedded credentials and machine-specific state; exclude local deliverables and runtime data.
- [x] Include append-only migrations 0006–0010 and verify generated OpenAPI/TypeScript consistency.
- [x] Backend: 215 tests passed, one optional integration test deselected; seven backup tests, Ruff/format and mypy passed.
- [x] Frontend: lint/types, five proxy tests, isolated production build and production dependency audit passed (zero reported vulnerabilities).
- [x] Retain the removed saved-view UI journey as explicitly skipped historical coverage; no automated E2E or Docker execution in this publication pass.

## Presentation cleanup — 2026-10-22

- [x] Remove the full-width saved-view bar from all shared CRM list screens.
- [x] Frontend lint/types pass; Chrome confirms cleaned pipeline before new deck screenshots.
- [x] Deliver the concise Relay hackathon PowerPoint with real Chrome screenshots and team credits, saved locally as `outputs/relay-hackathon.pptx` and copied to Downloads. Presentation files are not included in the source repository.

Presentation verification: eight slides rendered and visually reviewed; native editable text/diagram objects, six product screenshots and eight speaker-note sections; valid PPTX archive; all slide bounds/content-overlap checks passed. Both team names checked. The PowerPoint is an editable reconstruction of the Superdesign draft; font/layout rendering may differ across presentation apps.


## Hackathon workflow expansion — completed local scope

- [x] Durable scheduled multi-step automations with conditions, pause/cancel/retry, linked results and permission checks.
- [x] Typed custom fields, manager configuration, record editing and compatible conversion handoff.
- [x] Local lead capture forms, validated consent, duplicate handling and round-robin assignment connected to CRM events.
- [x] Integrate UI and honest connector catalog; regenerate contracts and run applicable backend/frontend checks.
- [x] Manually verify the new connected flows in Codex in Chrome; record actual outcomes and remaining limitations.

Actual verification: 211 combined backend tests passed (one optional integration test deselected); final changes additionally passed 23 intake/workflow, 20 customization and 44 CRM regression checks. Ruff/format (91 files), mypy (69 sources), final frontend lint/types, five proxy tests and final isolated production build passed. Chrome verified capture → assigned lead → task → delayed notification, custom value → converted contact, duplicate inquiry → two receipts/one lead, and persisted job results after restart. Full mobile/accessibility and every failure branch remain unverified in Chrome. No automated E2E, Docker or deployment run.

Next unchecked product items (outside the completed hackathon pass):

- [ ] Support intake, response/resolution SLA and customer portal.
- [ ] Product catalog, shared views/bulk actions, custom-field filtering/import/export and deeper reporting.
- [ ] External connectors remain deferred by explicit user instruction.

## Local connected CRM audit and build — active scope (2026-10-22)

Latest instruction: **local Chrome feature review only; no further automated E2E runs**. The combined automated suite was stopped. Docker/deployment/TLS/release work is outside this task. Earlier unchecked browser/deployment gates remain below as historical records and are superseded for the current session; they are not marked passed or silently resumed. Implementation checks below are separate from manual acceptance.

- [x] Research official commercial CRM documentation and open-source GitHub/docs; record major capabilities, gaps and links in `docs/CRM_AUDIT_2026-10-22.md`.
- [x] Implement/API-test quotations with exact server totals, immutable issued terms, decision history, print view and transactional optional acceptance-to-won; add migration 0006.
- [x] Implement/API-test sales forecasting with relevant close dates, weighted values, monthly breakdown, attention lists and paginated drill-through; synchronize open-stage probability changes to open deals.
- [x] Implement/API-test private saved views, validated filter presets and scoped update/delete; add migration 0007. List controls were integrated and verified, then removed during presentation cleanup; API/storage remain.
- [x] Connect CRM records, email templates and persisted unsent drafts; expose all supported automation triggers and compatible conditions.
- [x] Repair permitted assigned-record updates without exposing private linked customers; repair native date entry persistence; add Relay tab icon.
- [x] Final backend checks: 172 tests passed, one optional test deselected; mypy passed for 56 source files.
- [x] Final frontend lint, TypeScript, five proxy tests and isolated production build passed. Earlier nine frontend unit tests also passed.
- [x] Manual Chrome: signup → lead → linked contact/company/deal conversion → quotation create/issue/accept with deal won → forecast shows ₹1,25,000.50.
- [x] Manual Chrome: company overview → pre-linked dated task → correct My Day and Calendar entries.
- [x] Manual Chrome: search contacts for Mira → save private “Northstar contacts” view → reload → view exists and applies.
- [x] Manual Chrome: contact → recipient-prefilled email draft → save/reopen with contact retained → create/apply name/company/email template → resolved values saved. This remains an unsent draft.
- [x] Manual Chrome: company-linked support ticket → internal note → Resolved save; list retains Resolved status.
- [x] Manual Chrome: update saved filter/name, observe save confirmation, delete disposable view and observe deletion confirmation.
- [x] Manual Chrome: campaign creation with ₹5,000.50 budget → search/add existing converted Mira lead → one member, one converted lead and 100% conversion → remove membership → zero members; Leads list confirms Mira is unchanged. This verifies a pre-converted member, not conversion while enrolled or campaign revenue attribution.
- [x] Manual Chrome: create leads.created automation with one-day task → create Sam Fictional Inquiry → My Tasks shows “Review new customer inquiry” due 2026-10-23 → open confirms Sam lead link and automation note → complete → list status completed. Other triggers, condition branches and notification actions are not implied by this path.
- [x] Complete bounded local feature review and source-backed handoff in `docs/CRM_AUDIT_2026-10-22.md`. Exhaustive mobile/accessibility and every workflow permutation remain unverified.

No new runtime dependencies or provider credentials are required. Restart the local API for migrations `0006_quotations.sql` and `0007_saved_views.sql`. Future ERP, external communications and production readiness remain unclaimed.

## Related-record layout repair — 2026-10-22

- [x] Replace obsolete native-select spacing with an 8px grid gap; match search input sizing to the dropdown and preserve selection behavior.
- [x] Frontend lint and TypeScript checks passed; design hook reported no deterministic issues in the changed stylesheet.
- [ ] Live desktop/mobile visual confirmation of this narrow CSS change; browser verification stopped at the user's direction.

The latest user instruction supersedes the original Phase 0 approval stop and rigid ERP stack: deliver a working B2B sales and customer-support CRM now. The original ERP roadmap is preserved below as future scope, not a claim that those ERP modules exist. Implementation checks below mean the code is delivered; runtime browser acceptance is tracked separately and remains pending where the environment prevents it.

## Connected CRM coverage — historical session (2026-10-12)

Prioritize core B2B sales/support coverage for the hackathon. No additional role-matrix work is required in this pass; existing authentication, tenant isolation and backend checks remain in force. Checked implementation/API items below do not mark their separate browser acceptance complete. Evidence was collected in `artifacts/crm-coverage/ACCEPTANCE.md` (local-only audit output, not included in the source repository).

- [x] Parallel backend, relationship/campaign UI and workbench/pipeline UI ownership; root integration, independent contract review and preserved green-and-cream design.
- [x] Implement and API-test company/contact overview with real full totals, paginated related records/history and customer-linked creation actions.
- [x] Add migration `0005_campaign_members.sql`; implement and API-test real campaign membership, duplicate protection, scoped search/list/remove and converted-member metrics.
- [x] Implement and API-test My Day queues, task completion, real counts and paginated follow-ups/support links.
- [x] Implement and API-test configurable pipelines, protected stage outcomes/history, full board totals and per-stage pagination; preserve mandatory loss reasons and version checks.
- [x] Implement and API-test complete calendar date-range counts, bounded previews and paginated agenda with consistent search/status and IST date handling.
- [x] Repair integration issues found during review: empty-status calendar requests, calendar filter disagreement, filtering from later agenda pages, closed-stage deal creation and obsolete board test selectors.
- [x] Run backend suite: 136 passed, one optional PostgreSQL test deselected, one upstream warning; Ruff/format 56 files and mypy 42 sources passed.
- [x] Run frontend lint/types and nine unit tests; final isolated production build passed after all drawer-key, toolbar and pipeline-export fixes. No new dependencies.
- [x] Author four real-server browser journeys for customer context, campaign membership, pipeline configuration and 25-record calendar pagination; discover 19 tests across five files.
- [x] After user restart, verify My Day real counts/Due today and disposable signup → ₹45,000.50 lead → conversion → company list in live Chrome.
- [x] Confirm migration 0005 applied; remove only disposable QA tenant, with other tenant counts unchanged and foreign keys passing.
- [x] Independent desktop screenshot review; clarify task Complete action and IST due-date labels.
- [x] Live follow-up drawer regression: fix duplicate React keys; one company-prefilled drawer opens and zero remain after Cancel. Calendar day/search, board totals, loaded pipeline settings and campaign member search inspected read-only.
- [x] Match selected-pipeline CSV export across UI/API; 14 workspace + 4 existing import/export tests passed after this final change.
- [ ] Restart user-started API for final pipeline export patch and verify filtered download in Chrome.
- [ ] Complete live browser acceptance for customer overview → linked creation, campaign membership/conversion/removal, pipeline edits/board and calendar pagination/filters. Read-only checks above passed after Chrome recovered; mutation persistence and large-data browser pagination remain pending.
- [ ] Execute all 19 automated browser journeys after the required Chromium runtime is available. Discovery is not execution.
- [ ] Finish responsive/accessibility acceptance and deployment gates; update current coverage evidence with exact outcomes and any remaining blockers.

## End-to-end audit and repair — 2026-10-12

Local evidence: `artifacts/crm-audit/ACCEPTANCE.md` separates PASS, FAIL, BLOCKED and NOT IMPLEMENTED, with runtime evidence and outstanding scope. Audit artifacts are not included in the source repository.

- [x] Parallel UI, API/data and import/export ownership; independent combined-code review; preserve existing files and user's original Chrome login.
- [x] Repair CSV empty-filter exports, malformed/header/row validation, ambiguous duplicates, safe roundtrips and all-page sorting; verify persisted import/export data in real SQLite/API tests.
- [x] Live Chrome CSV upload: 1,000 rows → 980 records + 20 errors; retry → 0 created / 980 skipped; verify downloaded error file has 20 rows.
- [x] Live signup → private invitation → Read-only acceptance/login/refresh/logout, without external email; backend role/tenant/own-record permission tests pass.
- [x] Live lead edit and keyboard selection → conversion into linked company/contact/deal → loss reason; direct database confirmation.
- [x] Live task creation/completion; fix native date submission and verify saved date after reload; support priority/internal note/unsent reply draft persistence.
- [x] Fix invalid automation task links, ticket/contact/deal company integrity, ownership clearing, attachment retry duplication, engagement list pagination/search/sort.
- [x] Fix stale relationship results, read-only actions, assignment controls, notification/attachment states, invite state, paise display, explicit IST timestamps and misleading owner initials.
- [x] Capture real desktop screenshots and bounded keyboard/landing checks; preserve green-and-cream design.
- [x] Frontend lint/types, 9 unit tests, isolated `.next-audit` production build; backend lint/types/contracts and backup tests passed. See acceptance matrix for final backend count.
- [x] Remove disposable QA organization, its 2 fictional users and all its records atomically; foreign keys pass and every other tenant's table counts remain unchanged (`cleanup.json`).
- [ ] Run all 19 automated browser journeys: missing Chromium1243, attempted install failed DNS; prior runs stopped before assertions. Four current coverage journeys are authored/discovered, not executed.
- [x] After user restart, verify live CSV fixes: actual browser exports contain 980 unfiltered / 1 filtered rows; roundtrip skips all 980; malformed CSV rejects before partial writes. Other backend repairs still rely on the recorded API regression suite.
- [ ] Complete responsive/mobile/tablet and exhaustive accessibility/navigation/error-state checks. Viewport override had no effect in this session (actual1792×976); no new mobile PASS claimed.
- [ ] Enforce mandatory idempotency headers universally. Advanced permission expansion remains future scope by user direction; campaign membership and calendar dataset repairs are now implemented, with their new browser acceptance tracked above.
- [ ] Complete fresh-container/TLS/restore/dependency-advisory acceptance on an unrestricted runner. Gmail/sending remains explicitly deferred.

## Current CRM delivery

- [x] Inspect repository and local ProcessPay/August inspiration without overwriting existing work; use parallel agents with separate file ownership.
- [x] Real persistent backend, organization-scoped authentication, signup/login/logout and password/session management; no mock APIs.
- [x] Responsive Relay application shell with navigation, search, real notifications, real profile and explicit sample-data labeling.
- [x] Leads, contacts, companies, deal pipeline, tasks, calendar, campaigns and support CRUD connected to real backend routes.
- [x] Lead conversion into linked company/contact/deal; searchable relationship selectors and linked-record navigation.
- [x] Deal Kanban drag updates, stage edits, won/lost outcomes with loss reason; full server totals and independent per-stage pagination on the board.
- [x] Tasks completion, support internal notes versus unsent customer-reply drafts, activity history.
- [x] Live dashboard aggregates and reports, real empty/error/loading states, server-side list search/status filters/pagination.
- [x] CSV import/export with active filters and downloadable row error report, server sorting, editable records with version checks, request idempotency and confirmed delete action.
- [x] Live duplicate lead warning and confirmed merge into an existing lead; scoped attachment upload/download/delete on CRM records.
- [x] Email drafts/templates, credential-gated send behavior, conditional automation rules/toggle/execution logs and provider connection statuses.
- [x] Settings: user profile, password change, owner/admin team provisioning and integration status.
- [x] Optional explicitly fictional demo seed loads real records; application supports empty organizations.
- [x] Generated API contracts, frontend strict TypeScript, package lock, ESLint and Next production build.
- [x] Author real Playwright journey: signup → lead → convert → company/contact/deal → won → task completion → support note → logout; mobile auth layout check.
- [ ] Run Playwright journey and mobile checks against live API/UI. Latest attempt against the user-started 3007 server: Chromium headless shell revision 1243 is missing; ten tests stopped before assertions and its download failed DNS. Nineteen tests now discovered. Manual Chrome checks are recorded separately.
- [x] Capture actual desktop/mobile screenshots and complete bounded visual/keyboard verification in the user-started Chrome preview (2026-10-12); evidence in artifacts/ui-review. This is not a full accessibility certification.
- [ ] Verify local run script / Docker startup and provider-backed integrations with required environment access and credentials.
- [x] Record backend validation (56 tests passed; one optional PostgreSQL test deselected), static review and known runtime limitations in CHANGELOG.md.
- [ ] Complete final release acceptance after real browser journeys, visual review and fresh-container startup succeed.

## Landing and navigation review — 2026-10-12

- [x] Persistent workspace shell; scoped loading prevents false empty states; stale list/detail/search responses are discarded and failed requests can retry.
- [x] Shared custom dropdown across all CRM forms, filters, relationship selectors, invitations, roles and automation fields; keyboard selection, Escape, native FormData/validation support and viewport placement.
- [x] Public green-and-cream landing at `/`, authenticated workspace at `/dashboard`; responsive navigation, interactive journey tabs, FAQs and real entry links.
- [x] Live Chrome: all sidebar destinations, populated list transitions, dropdown keyboard and mouse interaction, mobile drawer menu placement/Escape, global search and record link, landing journey/FAQ/mobile navigation.
- [x] Real API check: create a clearly named disposable QA lead with Referral/Qualified selected, reopen and verify saved values, then delete it; original nine leads remain.
- [x] Report weighted-pipeline currency and win-rate formatting, meaningful labels, record drill-through; mobile search accessible label.
- [x] Independent desktop/mobile screenshot review, focusable journey panel fix, ESLint, TypeScript, five proxy tests and isolated standalone production build passed.
- [ ] Execute all 19 Playwright tests after installing the required Chromium runtime; no automated browser acceptance claimed.

## Deployment hardening — 2026-10-12

Implementation and verification are tracked separately. An unchecked release gate remains a blocker to calling this production-verified.

- [x] Reinspect existing work; parallel backend, CRM, frontend and independent static review with separate ownership.
- [x] Prepare standalone HTTPS production Compose, private API, persistent volume, health checks, unprivileged app images and rotating logs; validate Compose configuration.
- [x] Implement and test database/attachment backup, integrity/hash verification and restore to a new destination (7 tests passed).
- [x] Write deployment, first-owner setup, recovery and rollback instructions; add container and generated-contract checks to CI.
- [x] Complete API/static validation of authentication, invitation UI, sessions, tenant-state clearing, relational integrity and retry fixes: 79 backend tests, 7 backup tests, 5 proxy tests, lint/types/build and static confirmation passed. Browser acceptance remains separate.
- [ ] Run actual browser journeys including invitations and cross-account state isolation on a server-capable runner. The current preview is available through user-started Chrome; isolated Playwright runtime is missing. Manual interaction checks do not complete signup/invitation/cross-account acceptance.
- [ ] Build/start fresh containers, execute HTTP/browser journeys against the built frontend, issue a real TLS certificate, and complete a restore drill on the intended deployment host. Docker socket is inaccessible here.
- [ ] Complete connected dependency advisory checks; local npm audit failed with registry DNS resolution error.
- [ ] Complete release acceptance; no active user data or remote deployment has been modified in this session.

## Preserved original ERP roadmap

The following is the original, substantially larger ERP backlog. Its Phase 0 stop gate is historical and explicitly superseded by the latest CRM request. PostgreSQL ERP engines, accounting, GST, inventory, payroll and manufacturing are not represented as implemented by this CRM delivery.


Every business feature remains pending until its UI, API, database, validation, authorization, tenant isolation, UI states, module side effects and passing tests are complete, and CHANGELOG.md records it. Section references refer to the user's ERP_SPEC.md. Only explicit demo seeding may contain fictional business records. Preserve unchecked requirements across sessions; no silent scope reduction.

## Phase 0 — inspection, architecture and runnable foundation

- [x] P0.01 Run git status first and inspect the workspace; record empty directory/not a Git repository without resetting existing work (§0).
- [x] P0.02 Use multiple agents with non-overlapping file ownership; inspect available ProcessPay/August reference material without copying secrets (§0, user addendum).
- [ ] P0.03 Review complete PLAN.md: architecture, ownership, full tables/columns/relations/indexes, document flows, API list, folder structure, phases, decisions and dependency reasons (§0, §10–12).
- [x] P0.04 Create this exhaustive feature checklist and keep subsequent sessions anchored to the first unchecked item (§0).
- [x] P0.05 Create AGENTS.md preserving architecture, honesty, tests and definition of done (§3, §9, §15).
- [ ] P0.06 Verify Python 3.12/FastAPI/async SQLAlchemy 2/Pydantic v2 backend skeleton, Alembic migration scaffold and real health/readiness endpoints (§2, §14).
- [ ] P0.07 Verify PostgreSQL 16 with pg_trgm and pgvector extensions; apply migrations against an actual PostgreSQL instance (§2).
- [ ] P0.08 Verify Redis, Celery worker and Beat, MinIO private file storage, and Docker Compose one-command startup (§2).
- [ ] P0.09 Verify Next App Router strict TypeScript/Tailwind foundation with real readiness request; no simulated ERP screens (§2, §9).
- [ ] P0.10 Verify frontend package lock, lint, tsc, production build and meaningful Playwright foundation smoke (§2, §15).
- [ ] P0.11 Verify pytest/httpx, ruff, mypy, CI workflow, JSON logging and safe error envelope (§2, §11).
- [ ] P0.12 Generate Phase 0 health/error TypeScript contracts from real OpenAPI and detect schema drift; full business client remains P1.05 (§3).
- [ ] P0.13 Fresh-environment docker compose build/up, PostgreSQL migration upgrade, readiness and full-stack smoke pass; record environment blockers honestly (§15).
- [ ] P0.14 **STOP: user reviews Phase 0 and explicitly approves Phase 1.** Do not start business feature implementation before approval (§0, §14).

## Phase 1 — platform and shared engines

- [ ] P1.01 Enforce modular monolith boundaries, module table ownership and routers → services → repositories → models; no router DB calls (§3).
- [ ] P1.02 Tenant base repository enforces org_id on every business query/write; another org's ID yields 404; scope background jobs, attachments, search, exports and polymorphic links (§3, §7).
- [ ] P1.03 Standard UUID/org/audit timestamps/actors; soft-delete masters only, immutable posted records; UTC storage, Asia/Kolkata default display and configurable April–March FY (§3).
- [ ] P1.04 Decimal money (18,2), quantities (18,3), rates (18,4); authoritative server arithmetic; round-off ledger; Indian number/₹ lakh/crore formatting with setting (§3).
- [ ] P1.05 OpenAPI-generated full TypeScript client used by UI; replace constrained Phase 0 generator with maintained generator; strict schema drift CI (§3).
- [ ] P1.06 Atomic multi-table transactions; required Idempotency-Key on creates/submissions/payments; payload conflict handling; row locks/version conflicts (§3).
- [ ] P1.07 Transactional outbox, Celery dispatch, idempotent event handlers, retry/dead-letter visibility and recovery; no duplicate business effects (§3).
- [ ] P1.08 Signup atomically creates org/owner; Argon2 passwords; JWT access/refresh in httpOnly cookies; refresh rotation, CSRF, safe auth responses (§5.1, §7).
- [ ] P1.09 Email invites with acceptance; password reset; active session list, revoke session, logout all and user deactivation (§5.1).
- [ ] P1.10 Org → company (PAN/legal entity) → branch (state/GSTIN) → warehouse; switcher authorization and tenancy (§3, §5.1).
- [ ] P1.11 Editable Owner/Admin/Accountant/Sales Manager/Sales Rep/Purchase/Store Keeper/Support Agent/HR/Read-only CA roles (§5.1).
- [ ] P1.12 Backend module × action permissions: view/create/edit/submit/cancel/delete/approve/import/export/manage settings; least privilege (§5.1, §7).
- [ ] P1.13 Own/team/branch/all record visibility; teams/members; enforce on individual/list/bulk/search/report APIs and UI (§5.1).
- [ ] P1.14 Field access for cost price, margin and salary in serializers, filters, reports, exports and UI (§5.1).
- [ ] P1.15 Company/branch GSTIN/PAN/logo, currency/timezone/FY/number format settings (§5.1).
- [ ] P1.16 Configurable numbering, tax templates, payment terms, units, default ledgers, lead statuses/sources/pipelines/activity types/tags settings (§5.1).
- [ ] P1.17 Append-only actor/action/entity/time/field/old/new audit log; audit admin actions, redact secrets and personal data (§5.1, §7).
- [ ] P1.18 Authorized S3 attachments with size/type checks, private storage and secure scoped download (§5.1, §7).
- [ ] P1.19 Notification bell/email, read state/preferences; assignments, mentions, task due, approvals, stage changes, low stock, overdue payment, failed jobs; retry dedupe (§5.1).
- [ ] P1.20 Ctrl+K scoped global search, recently viewed and real empty states; indexed names/phone/email search (§5.1).
- [ ] P1.21 CSV/Excel import mapping/preview/validation/background progress; skip/update/create dedupe; atomic row writes and downloadable error report (§5.1).
- [ ] P1.22 Background export respects filters, field/record permissions and tenancy; CSV/Excel framework (§5.1).
- [ ] P1.23 Document Draft → optional Pending Approval → Submitted → Cancelled engine; draft edits only; submitted lock (§4).
- [ ] P1.24 Cancellation reversals and amendment copy linked to source; no deletion of posted documents; idempotent lifecycle (§4).
- [ ] P1.25 Numbering per type/branch/FY, configurable prefix; GST sequential unique FY number ≤16 characters; never reuse cancelled numbers (§4).
- [ ] P1.26 Line-item component includes item/description/HSN-SAC/qty/UoM/rate/discount/tax/amount; server preview totals (§4, §6).
- [ ] P1.27 Document relation chain and conversion framework tracks only pending quantities; guards over-delivery/over-billing (§4).
- [ ] P1.28 August Design System inspection/adaptation or documented shared tokens; shadcn/ui primitives introduced with reasons (§2, §6).
- [ ] P1.29 Responsive collapsible module sidebar; top bar company/branch switcher, search, + New, notifications/profile; no dead controls (§6).
- [ ] P1.30 TanStack Query/Table reusable server-side search/filter/sort/cursor pagination, row selection, bulk actions, columns, badges/actions (§2, §6).
- [ ] P1.31 react-hook-form/zod forms: labels/required markers/inline errors/searchable selects/date/currency/custom slots/unsaved warning (§2, §6).
- [ ] P1.32 Keyboard document grid: Tab cells, Enter adds row, item search name/SKU/barcode, totals/tax breakup, status/chain/print preview (§6).
- [ ] P1.33 Record page header/status/owner/actions, inline edits, timeline/related/history; reusable components (§6).
- [ ] P1.34 Every implemented screen: loading/empty/error/denied/validation/success/long text/large data; mobile/contrast/focus/keyboard; professional icons, plain English, tel:/wa.me links; print white (§6).
- [ ] P1.35 Shared REST entity list/create/get/patch/delete/bulk/import/export with server filtering/sorting/cursors and consistent error envelope (§11).
- [ ] P1.36 /me, /me/tasks, search, dashboard/report route contracts; enforce immutability/unsupported actions explicitly (§11).
- [ ] P1.37 Auth/public rate limits, validated inputs, injection/XSS/CSRF defenses, safe responses without stack traces/SQL; masked logs (§7).
- [ ] P1.38 Real structured JSON logs, request correlation and optional Sentry wiring without secrets (§2).
- [ ] P1.39 Phase 1 applicable acceptance/tests/lint/types pass; CHECKLIST and CHANGELOG updated (§15).

## Phase 2 — CRM core and customer masters

- [ ] P2.01 Customer-side unified parties with customer/vendor flags, parent/child, account health, renewal date and real revenue summary (§5.2–3).
- [ ] P2.02 GSTIN format/checksum/state/PAN derivation; PAN, multiple billing/shipping addresses/states, credit/payment terms/price list/opening balance/contacts (§5.3).
- [ ] P2.03 Leads: name/email/E.164 phone (+91 default), company/title/website/industry/size/city/state, source/campaign, status/rating/score/owner/team (§5.2).
- [ ] P2.04 Leads: estimated value/budget/timeline/next follow-up/tags/custom fields; configurable New/Contacted/Qualified/Unqualified/Converted defaults (§5.2).
- [ ] P2.05 Lead assignment round-robin and state/source rules with concurrency-safe fairness; response-time tracking (§5.2).
- [ ] P2.06 Same phone/email duplicate detection/warning; merge preserves history, links, ownership and audit (§5.2).
- [ ] P2.07 Lead conversion atomically creates or links contact/customer/deal; repeated conversion creates no duplicates (§5.2, §11).
- [ ] P2.08 Contacts: multiple emails/phones, designation/party/primary flag, consent source/communication preferences, owner/timeline (§5.2, §7).
- [ ] P2.09 Multi-pipeline deals with stages, probability and required fields; dnd-kit Kanban + table; server-valid stage drag/history/audit (§2, §5.2).
- [ ] P2.10 Deal aging/stale alerts, won/lost mandatory reason, closed exclusion from open pipeline, weighted amount × probability (§5.2).
- [ ] P2.11 Task/call/meeting/email/note/follow-up activities linked polymorphically to records; My Day overdue/today/upcoming (§5.2).
- [ ] P2.12 Day/week/month calendar; recurring tasks, reminders, mentions, assignment and call logging/outcome (§5.2).
- [ ] P2.13 Tags/entity tags and customizable activity/status/source vocabulary with permission checks (§5.1–2).
- [ ] P2.14 AND/OR filters on all supported fields, personal/shared saved views, column configuration, scoped bulk actions (§5.1).
- [ ] P2.15 CRM sales dashboard real pipeline/targets/tasks, date/previous period filters and drill-through (§5.11).
- [ ] P2.16 CRM funnel/source/win-loss/rep reports; honest no-data states and CSV/Excel/PDF exports (§5.11).
- [ ] P2.17 Public lead form definition + POST /public/forms/{id}/submit, CAPTCHA verification/rate limit/consent; no duplicate retry submissions (§11).
- [ ] P2.18 Phase 2 applicable acceptance/tests pass; UI/API/DB/permissions and CHANGELOG completed (§15).

## Phase 3 — masters, accounting and inventory engines

- [ ] P3.01 Vendor role extends same parties; party addresses/contacts and dual customer/vendor use without duplicates (§5.3).
- [ ] P3.02 Goods/service items: SKU, HSN/SAC, groups/brand/UoM/conversions/GST/purchase-sales prices, batch/serial flags (§5.3).
- [ ] P3.03 Items: reorder level, valuation method/default warehouse/barcode; item groups, price lists/item prices/discount rules (§5.3).
- [ ] P3.04 Configurable tax rates/templates/payment terms/UoM conversions; no hardcoded business rates (§5.3).
- [ ] P3.05 Indian chart of accounts: editable Assets/Liabilities/Income/Expenses/Equity; Debtors/Creditors/Duties-Taxes/Bank/Cash groups (§5.7).
- [ ] P3.06 One GL engine; Decimal balanced debit=credit invariant, immutable posting/reversals, vouchers/source on every line (§5.7, §10).
- [ ] P3.07 Journal/payment/receipt/contra/debit-note/credit-note vouchers; cost centres, opening balances/fiscal years (§5.7).
- [ ] P3.08 Ledger-only general ledger/day book/party ledger/cash-bank book/trial balance; no document-derived accounting totals (§5.7).
- [ ] P3.09 Immutable stock entries item/warehouse/batch/in-out qty/rate/value/voucher type/id; balances updated in same transaction (§5.6, §10).
- [ ] P3.10 Moving weighted-average default and FIFO company option; valuation layers/reversal/backdated-entry policy covered (§5.6).
- [ ] P3.11 Batches/expiry and serial traceability, warehouse segregation and UoM conversion consistency (§5.6).
- [ ] P3.12 Opening stock, warehouse transfer, adjustment with reason+approval hook, stock counts and variance posting (§5.6).
- [ ] P3.13 Negative stock blocked unless explicitly allowed; lock-safe final-unit concurrency and clear API/UI failure (§3, §5.6).
- [ ] P3.14 Stock balance/valuation/movement/aging/slow-moving reports and reorder alerts (§5.6).
- [ ] P3.15 Highest-coverage posting/stock/tax/numbering/document tests; transaction rollback, race and idempotency coverage (§15).
- [ ] P3.16 Phase 3 applicable acceptance/tests pass; CHECKLIST and CHANGELOG updated (§15).

## Phase 4 — sales, purchase and GST document flows

- [ ] P4.01 Quotation → sales order → delivery note → GST sales invoice → payment receipt with all item tables (§5.4, §10).
- [ ] P4.02 Direct invoices/advance receipts, multiple invoice allocation/partial payments, unapplied balances/refunds (§5.4).
- [ ] P4.03 Pending-only conversion, partial delivery and billing, partly/fully delivered/billed statuses and linked chain (§4, §5.4).
- [ ] P4.04 Credit limit warn/block setting, customer statements and ledger-derived AR aging (§5.4).
- [ ] P4.05 Sales returns/credit notes reverse applicable physical stock/tax/receivables without double stock movements (§5.4).
- [ ] P4.06 Purchase requisition → PO → GRN → purchase bill → vendor payment with item tables (§5.5, §10).
- [ ] P4.07 PO/GRN/bill three-way quantity+rate match; discrepancy flags and allowed-variance policy (§5.5).
- [ ] P4.08 Purchase returns/debit notes, vendor advances/partial allocations and ledger-derived AP aging (§5.5).
- [ ] P4.09 PO value approvals block submission appropriately; configurable manager threshold (§5.5).
- [ ] P4.10 Receipt/delivery/returns invoke real stock engine and valuation; no document status preceding committed effects (§3–5).
- [ ] P4.11 Automatic invoice Dr Customer/Cr Sales/Cr Output GST; bill Dr Purchase or Stock/Dr Input GST/Cr Vendor (§5.7).
- [ ] P4.12 Perpetual delivery Dr COGS/Cr Stock; receipts/payments/advances/returns and Round-Off postings via single engine (§5.7).
- [ ] P4.13 Line tax from configured HSN/SAC rates; explicit permission to override (§5.8).
- [ ] P4.14 Supplier state = place of supply → CGST+SGST or applicable UTGST; interstate → IGST; exports/SEZ zero-rated treatments (§5.8).
- [ ] P4.15 Reverse-charge purchase flags; B2B/B2C/unregistered; place-of-supply validations and tax rounding (§5.8).
- [ ] P4.16 Statutory code marked # VERIFY-WITH-CA and versioned/configurable; CA review of actual current statutory requirements (§5.8).
- [ ] P4.17 WeasyPrint HTML/PDF letterhead, logo, white background and required GST invoice fields, print preview (§2, §4).
- [ ] P4.18 Email document PDF through real provider; confirmed delivery status, permission/attachment scope and retry dedupe (§4, §5.2).
- [ ] P4.19 Cancel creates GL/stock reversals, locked cancellation retains number; amend links new draft to original (§4).
- [ ] P4.20 All document REST submit/cancel/amend/convert/pdf/links/email actions implement lifecycle permissions/idempotency (§11).
- [ ] P4.21 Phase 4 full order-to-cash/procure-to-pay and tax acceptance tests pass; CHECKLIST/CHANGELOG updated (§15).

## Phase 5 — controls, compliance and reporting

- [ ] P5.01 Reusable approval engine/rules/requests, conditions, approve/reject comments and audited authority; documents remain blocked while pending (§4).
- [ ] P5.02 Reusable trigger → conditions → actions automation; validation before enable; execution log/retries/idempotency/max-depth loop prevention (§5.1).
- [ ] P5.03 Custom definitions + JSONB: text/long text/number/currency/date/datetime/boolean/single-select/multi-select/email/phone/URL/user (§5.1).
- [ ] P5.04 Custom fields function in forms/validation/AND-OR filters/exports/reports with GIN indexes and authorization (§5.1, §8).
- [ ] P5.05 Bank accounts/CSV-Excel statements/dedupe/import diagnostics, match suggestions and manual/automatic reconciliations (§5.7).
- [ ] P5.06 Ledger-only P&L/balance sheet/cash flow and AR/AP aging/DSO/DPO; reconcile each report to GL (§5.7).
- [ ] P5.07 Cost-centre reporting, period locks (all posting/reversal routes) and repeat-safe FY close/carry-forward (§5.7).
- [ ] P5.08 Sales/purchase registers, HSN summary, GSTR-1 GST-portal JSON/Excel, GSTR-3B summary and ITC summary; prepares data only, never fake filing (§5.8).
- [ ] P5.09 GSTR-1 export totals reconcile to sales register and GL tax accounts with current schema validation (§5.8, §15).
- [ ] P5.10 Owner dashboard sales/receivables/payables/cash-bank/stock/top customers (§5.11).
- [ ] P5.11 Sales dashboard pipeline/targets/tasks; Accountant overdues/unreconciled bank/GST payable; Store low stock/pending deliveries-GRNs (§5.11).
- [ ] P5.12 All dashboard/report figures use real scoped data, date/previous period comparison, click-through records and proper no-data states (§5.11).
- [ ] P5.13 Sales/purchase/inventory/accounting/GST reports; background CSV/Excel/PDF heavy exports and scheduled report delivery (§2, §5.11, §8).
- [ ] P5.14 Phase 5 reconciliation/period lock/approvals/automation/custom field tests and all applicable acceptance pass (§15).

## Phase 6 — advanced CRM and communication

- [ ] P6.01 Campaigns with type/budget/dates/members/attribution; cost per lead and ROI based only on recorded actual data (§5.2).
- [ ] P6.02 Tickets with number/priority/category and New/Open/Pending/Resolved/Closed states; SLA clocks/breach/escalation (§5.2).
- [ ] P6.03 Separate internal ticket notes from customer replies; support-agent permissions and SLA reports (§5.2, §5.11).
- [ ] P6.04 Forecast by rep/team/pipeline/month/quarter, commit/best-case/pipeline, targets, snapshots and forecast-vs-actual (§5.2).
- [ ] P6.05 SMTP/API email templates with validated merge fields, email message/provider status; never mark sent on click (§5.2).
- [ ] P6.06 WhatsApp Business boundary, credential settings, verified messages/status callbacks, templates/consent and setup docs (§5.2, §5.12).
- [ ] P6.07 All phase 6 connectors settings/status/validation/retries/sync state/dedupe/encrypted credentials/disconnect; disabled until credentials (§5.12).
- [ ] P6.08 Phase 6 CRM advanced/communication/support tests and acceptance pass (§15).

## Phase 7 — integrations, HR, optional manufacturing and AI

- [ ] P7.01 Shared connector contract: settings/connection status/validation/retries/sync status/dedupe/encrypted secrets/disconnect and credential-gated activation (§5.12).
- [ ] P7.02 Google sign-in and 2FA with secure enrollment, recovery and revoke flows (§5.1).
- [ ] P7.03 Gmail/Outlook email+calendar OAuth sync, cursor checkpoints, token refresh/revocation, conflict/dedupe rules (§5.2, §5.12).
- [ ] P7.04 Payment links (Razorpay adapter), verified signature webhook/invoice matching, amount/currency checks and idempotent settlement (§5.12).
- [ ] P7.05 GSP e-invoice IRN/QR + e-way bill boundary/settings/adapters; credentials required, provider-confirmed status, never fake IRN (§5.8, §5.12).
- [ ] P7.06 Pluggable Tally masters/vouchers import/export; validation/mapping/reconciliation and connector setup docs (§5.12).
- [ ] P7.07 Public scoped API keys/rotation/revoke/rate limits and documented REST; outgoing HMAC webhooks with retries/replay/delivery logs (§5.12).
- [ ] P7.08 POST /webhooks/{provider} signature verification/raw body handling/replay prevention; no provider success without confirmed evidence (§11).
- [ ] P7.09 TDS/TCS configurable sections/rates/effective dates and applicable postings/reports; CA-reviewed logic (§5.8).
- [ ] P7.10 Item variants with attributes, inventory/SKU/pricing rules and migration compatibility (§5.3).
- [ ] P7.11 Employees/departments/designations/attendance/holidays; leave types/balances/applications and approvals (§5.9).
- [ ] P7.12 Salary structures/components Basic/HRA/allowances/PF/ESI/state PT/TDS; rates configured, effective-dated and CA-reviewed (§5.9).
- [ ] P7.13 Payroll run/approval/payslip PDF/payroll journal, transactional/idempotent processing; salary visible only HR/Owner (§5.9).
- [ ] P7.14 Optional final manufacturing: multi-level BOM with cycle detection, work orders/material issue/production consumes raw materials and produces finished goods at rolled cost/scrap (§5.10).
- [ ] P7.15 Single AI service layer with per-org off switch/provider settings/data access controls and audit (§5.13).
- [ ] P7.16 AI natural-language search, email drafts and call-note summaries/tasks requiring appropriate review (§5.13).
- [ ] P7.17 AI deal risk/lead score and pgvector duplicate detection with tenant isolation and explainable provenance (§5.13).
- [ ] P7.18 Bill photo/PDF extraction creates draft purchase bill only; user confirmation and attachment permission checks (§5.13).
- [ ] P7.19 Integration setup docs for missing credentials; live verification remains explicitly unchecked until real credentials/evidence (§5.12).
- [ ] P7.20 Phase 7 applicable connector/payroll/AI/manufacturing tests and acceptance pass (§15).

## Phase 8 — hardening, seeded validation and release

- [ ] P8.01 Recheck every endpoint for tenant/record/field permissions and least privilege; cross-tenant IDs 404; admin audit (§7).
- [ ] P8.02 Security review of passwords/cookies/session rotation/OAuth/API secret encryption/auth-public throttling/CSRF/XSS/injection/upload/download (§7).
- [ ] P8.03 Audit/log secret exclusion and phone/email/PAN/bank/salary masking; safe error envelope everywhere (§7).
- [ ] P8.04 DPDP consent source, full person data export, deletion/anonymization workflows; legal-retention configuration and anonymized preserved posted documents (§7).
- [ ] P8.05 Composite org+owner/status/date/party/item/warehouse indexes; trigram name/phone/email and JSONB GIN; query plan checks (§8).
- [ ] P8.06 No N+1; server-side filtering/sorting/pagination for every list; background imports/exports/bulk PDFs/heavy reports (§3, §8).
- [ ] P8.07 Opt-in 100k-record-per-org load seed; representative permission/filter lists under 500ms under documented hardware/concurrency; performance evidence (§8).
- [ ] P8.08 Lazy-load heavy frontend modules; mobile sales/store workflows, contrast/focus/keyboard accessibility and screen-state audits (§6, §8).
- [ ] P8.09 Idempotent explicitly labelled fake Indian demo seed: fictional names/cities, valid-format checksum GSTINs, two branches in different states (§13).
- [ ] P8.10 Demo parties/items/stock/deals all stages/full flow documents/tasks/tickets; seed twice without duplicates, no real credentials/default production admin (§13).
- [ ] P8.11 Completely empty database works with proper empty states and first-run setup (§13).
- [ ] P8.12 API/tenant/permissions/concurrency/idempotency/import/automation tests and Playwright main journey coverage; engine coverage prioritized (§15).
- [ ] P8.13 Fresh-clone deployment guide, env/credential setup, backup/restore drill, migration/rollback recovery, monitoring/jobs troubleshooting and API docs (§14).
- [ ] P8.14 Complete table inventory/migrations verified against minimum §10; polymorphic links and source-document columns intact (§10).
- [ ] P8.15 Every new dependency justified in PLAN; each schema change new migration; no applied migration edited/deleted; no fake metrics/auth/records/dead controls/empty catches (§9).
- [ ] P8.16 Final tests/lint/type checks/Docker startup and all acceptance checks below pass; update CHECKLIST/CHANGELOG (§15).
- [ ] P8.17 Honest session/release report: completed features/files/architecture/migrations/setup/env/credentials/tests/gaps/next unchecked work (§16).

## Acceptance checks — rerun applicable checks at every phase boundary

- [ ] A01 Signup → org → invite → invited user logs in (Phase 1+).
- [ ] A02 Own records enforced in UI and API; other-org record ID is 404 (Phase 1+).
- [ ] A03 Same-phone lead warning; atomic contact/customer/deal conversion; second conversion creates nothing (Phase 2+).
- [ ] A04 Deal drag persists stage history + audit; lost requires reason; closed excluded from open pipeline (Phase 2+).
- [ ] A05 Import 1,000 rows with 20 bad → 980 created, downloadable error file (Phase 2+).
- [ ] A06 Quotation → SO → partial delivery → invoice → part payment → full payment: correct stock valuation, zero customer balance, balanced journals, correct delivery/billing statuses (Phase 4+).
- [ ] A07 Same-state CGST+SGST and other-state IGST match hand calculation including round-off (Phase 4+).
- [ ] A08 PO → GRN → different-rate bill → payment flags three-way mismatch; correct stock/weighted average (Phase 4+).
- [ ] A09 Credit note reverses applicable stock/tax/receivable (Phase 4+).
- [ ] A10 Submitted invoice cancel creates reversals; number retained/not reused; read-only document (Phase 4+).
- [ ] A11 Double-click Submit creates one invoice (Phase 4+).
- [ ] A12 Two users sell final unit: exactly one succeeds, clear other error, no negative stock (Phase 3+).
- [ ] A13 Locked-period posting blocked (Phase 5+).
- [ ] A14 Seed trial balance balances; P&L profit equals balance-sheet movement (Phase 5+).
- [ ] A15 GSTR-1 export totals equal sales register totals (Phase 5+).
- [ ] A16 Sales Rep cannot see cost; high-value PO waits for approval (Phase 4+).
- [ ] A17 Every dashboard figure equals direct DB query on seed data (Phase 5+).
- [ ] A18 Tests/lint/types and fresh-clone docker compose up pass (every phase with applicable scope).

## Current limitations

The original Phase 0 review boundary is superseded for the current CRM delivery. Future ERP business features below remain pending; no checkbox claims implementation merely because a plan or table definition exists. Environment-limited checks stay unchecked with actual details in CHANGELOG.md and the session report. Manufacturing remains in scope as optional, unchecked until implemented or explicitly declined by the user.
