# Relay CRM implementation plan

## Current delivery: B2B sales and customer support

The user's later instructions supersede the original ERP-first, strict-stack and Phase 0 review-stop requirements. The active deliverable is a working CRM suitable for a hackathon, with polished UX, a real persistent backend, B2B sales and customer support. Gmail connection is explicitly deferred. Continue implementation now; do not stop for the former Phase 0 review. ProcessPay is one inspiration reference, not a source of truth. The ERP design below is retained as a **future architecture proposal**, not a current delivery promise or a description of implemented behavior.

### Current priority: connected CRM coverage (2026-10-12)

The user's latest direction prioritizes an end-to-end hackathon CRM over further role-matrix expansion. Keep existing authentication, tenant isolation and backend checks; do not spend this delivery on additional granular roles. Email remains a future push/pull integration, not a substitute for connected customer workflows.

Implemented in this pass:

- Company/contact **Customer overview** combines scoped contacts, deals, tasks, tickets, converted leads and unified audit history. Server totals cover all matching records; related lists are paginated. Contextual actions create a pre-linked follow-up, deal or ticket through the existing editor.
- Campaign **Members** supports real lead/contact search, duplicate-safe membership creation, removal without deleting the original record, pagination and conversion counts. Conversion means a member lead reached Converted; this does not claim causal revenue attribution or campaign ROI.
- **My Day** at `/workbench` groups overdue/today/upcoming tasks, lead follow-ups, deals in the same stage for 14 days, open support and unassigned support. Queues have real server counts, scope selection, pagination, record links and task completion.
- **Pipeline settings** at `/pipelines` creates and edits named sales processes, stage order and probability. Won/Lost outcomes stay protected; stages referenced by deals/history cannot be deleted. The board selects a pipeline, calculates full stage totals and independently pages each stage, with drag and keyboard-accessible move controls.
- The calendar displays a 42-day grid with complete per-day counts and bounded previews, plus a paginated day agenda. Search/status are applied consistently to both summary and agenda; date-only tasks retain their date and timestamped tasks group in Asia/Kolkata.

**Decisions:** extend existing modules and authored CSS without new dependencies; keep real SQLite persistence and existing domain checks. Use migration `backend/local_migrations/0005_campaign_members.sql` for campaign membership, never edit applied migrations. New frontend views use scoped CSS and existing Select/API helpers; ordinary record editing stays in the shared editor. Backend coverage lives in `backend/app/modules/crm/workspace.py`, with scoped repository filters and regression tests.

**API additions:** `GET /{parties|contacts}/{id}/overview?limit=&offset=`, `GET|POST /campaigns/{id}/members`, `DELETE /campaigns/{id}/members/{membership_id}`, `GET /workbench?queue=&owner_id=&limit=&offset=`, `GET /calendar?from_date=&to_date=&q=&status=`, `GET /deals/board-summary?pipeline_id=&q=`, `PATCH /pipelines/{id}`. Existing collection filters add pipeline and activity date-range selection. Existing `POST /pipelines` creates a process.

**Verification:** backend 136 passed, one optional PostgreSQL test deselected, one upstream warning; Ruff/format 56 files and mypy 42 sources passed. Frontend lint, types and nine unit tests passed. Isolated production build passed before the final narrow pipeline-editor adjustment, which subsequently passed lint/types. Four new real-server Playwright journeys bring discovery to 19; automated browser execution remains blocked by the missing Chromium runtime. After the user restarted the app, live Chrome verified My Day counts/Due today and a disposable signup → ₹45,000.50 lead → conversion → company list. The remaining new browser journeys are still in progress and must not be claimed complete.

**Next work:** finish new-feature browser acceptance, run the authored browser suite on a capable runner, and record exact outcomes in `artifacts/crm-coverage/ACCEPTANCE.md`. Previous audit/deployment evidence remains historical and does not automatically certify these additions. Saved views, custom fields, recurring reminders, advanced SLA/forecasting, live communications and production deployment verification remain separate gaps.

### Implemented direction and boundaries

- FastAPI application with real SQLAlchemy 2 models, SQLite persistence in the runnable local profile, append-only numbered local SQL migrations, real cookie sessions/password hashing and organization isolation. PostgreSQL/Redis/Celery scaffold remains a future deployment path, not a claim that the live CRM uses asynchronous jobs.
- Backend modules: `auth` owns organizations/users/sessions and authentication; `crm` owns typed leads, contacts, B2B accounts (`parties`), deals, pipelines/stages/history, tasks/calls/meetings/notes, campaigns and support tickets/conversation; `engagement` owns automation, notification and email draft/integration-boundary records; `files` owns private attachment metadata and local file storage.
- Shared tenant-aware CRM repository scopes reads, updates, linked references, search, exports and own-record roles. Services validate exact Decimal values, E.164 phone normalization, permitted status changes and linked records. Lead conversion creates an account, contact and optional deal in one transaction and repeat conversion returns existing linked records. Duplicate-lead merge validates both records, archives the source, preserves the target, and moves activities, files and drafts in one transaction while retaining audit history.
- Deal updates record stage history and audit; lost deals require a reason. Dashboard totals aggregate the full permission-scoped database, not a browser page. Optional all/7/30/90-day filters describe the record-creation cohort explicitly. Closed deals are excluded from open pipeline value. Server search/filter/sort/pagination, CSV imports with per-row savepoints and error reports, exports, record timelines and soft delete are real persistence operations.
- Support tickets link accounts, contacts and deals, separate internal notes from reply drafts, track priority/status and resolution timestamps. Without a connected mail provider, replies are stored as drafts and never displayed as delivered.
- Synchronous transactional automation evaluates CRM events, records runs and creates persisted tasks/notifications without recursive event loops. This simple in-process execution is the implemented hackathon boundary; the outbox/Celery architecture below is future ERP work.
- Frontend uses Next.js App Router and strict TypeScript with a reusable CRM shell, dashboard, searchable records, pipeline board, editors, detail views, tasks, support, reports and settings. Empty, loading, validation, failure and permission states are required; no fake metrics.

### Active work sequence

1. Finish the first unchecked item in the current CRM coverage section of CHECKLIST.md: new-feature browser acceptance; retain the earlier implementation sequence below as context.
2. Inspect workspace, ProcessPay reference and official online documentation; establish real persistence/auth and shared contract.
3. Complete CRM core APIs and transactions; frontend CRUD, lead conversion, deal progression, activity completion and support conversation.
4. Add real dashboard/report aggregates, CSV data portability, safe automations, email drafts and provider setup states.
5. Run real SQLite API/transaction/isolation/import/automation tests, frontend type/build checks and available browser verification. Fix failures, document actual tool/runtime limitations.
6. Deliver setup commands, actual test results, known gaps and remaining integrations; preserve the future ERP plan below separately from current claims.

### Final coverage repair decisions (2026-10-12)

- Editor and automatic-create components use separate React key namespaces, preventing duplicate drawers when contextual creation clears its URL query.
- Board and calendar hide generic controls they do not implement. Deal export scopes to the selected pipeline; switching back to Board clears hidden table status. The last API patch requires a backend restart; it does not require another migration.
- Live read-only checks and API tests are distinguished from new browser mutation acceptance in `artifacts/crm-coverage/ACCEPTANCE.md`. No new dependency was added.

### Current decisions and limitations

- User-authorized CRM-first scope takes precedence over the earlier ERP build order and Phase 0 stop. No accounting, stock, payroll, GST filing or manufacturing is claimed by this CRM delivery.
- Sync SQLAlchemy with SQLite provides real durable local operation using available packages. This is an explicit pivot from the original asynchronous PostgreSQL requirement. SQLite has single-writer limits; multi-instance/high-load production deployment is future PostgreSQL work.
- Real user-created records are the default. Optional fake demonstration records, if seeded, must be explicitly labelled and use an opt-in seed path. No production admin credential is embedded.
- Provider authentication and Gmail mailbox sync are deferred by user direction; saved email/support drafts are not sent. Integration UI must accurately state this.
- Session/tenant/action checks run on the server. Current role support is narrower than the original full editable ERP permission matrix; do not advertise that future matrix as implemented.
- Full text search is SQL-backed for the SQLite profile. pg_trgm, pgvector and AI are future integrations.
- Tests and validation results are recorded in the session report and `CHANGELOG.md`; creating routes or passing compilation alone does not complete user journeys.

### Audit repair decisions (2026-10-12)

- The full audit uses disposable tenant data and actual Chrome against the user's existing server. QA used `localhost` to avoid replacing the user's `127.0.0.1` cookie session; all QA records/users were removed afterward with unchanged other-tenant counts.
- CSV is the active portable-data format. Malformed/ambiguous input is rejected; schema fields roundtrip with safe formula escaping and JSON tags. Lifecycle actions remain service commands; CSV does not restore converted leads or recreate already-closed deals.
- Native date input values are read at form submission so browser picker/autofill values cannot silently disappear when a change event is missing. Date-only values remain date-only. Stored timestamps display explicitly in Asia/Kolkata (IST); per-user timezone preferences remain future work.
- `NEXT_DIST_DIR` isolates production and automated-test outputs from the live `.next` directory. Playwright's default server uses temporary SQLite/uploads and a distinct `.next-e2e-*` directory. Browser installation/network and socket permissions remain external verification constraints.
- No new runtime dependency or database migration was needed. Existing idempotency storage/services support attachment retry protection and other covered creates. API keys remain optional for compatibility, so the original universal required-key contract is not claimed.
- See `artifacts/crm-audit/ACCEPTANCE.md` for acceptance evidence, remaining scope and exact run commands.

### Deployment hardening decisions (2026-10-12)

- Production is a single host with persistent SQLite and private upload storage. A standalone production Compose definition adds a Caddy 2.11.2 HTTPS reverse proxy; it is infrastructure for TLS certificate management and security headers, not a new application service boundary. Only ports 80/443 are public. Public signup is disabled by default and the owner is provisioned with an interactive CLI. An audited operator-only password recovery CLI revokes all sessions; it does not impersonate an email reset integration. Password hashing is upgraded on successful login while existing hashes remain compatible.
- Backup/restore uses the Python standard library and SQLite backup API. API writers must be stopped while creating a consistent database-plus-files snapshot. Restore writes only to a new destination and verifies database integrity, foreign keys and attachment checksums before completion. Backups contain personal data and require restricted access and encrypted off-host retention.
- The SQLite profile accepts money up to ₹999,999,999,999.99 to keep individual cent values within safe storage precision; dashboard arithmetic is performed using Decimal rather than floating SQLite sums. Full NUMERIC(18,2) range remains a future PostgreSQL concern.
- Production container startup, TLS issuance and browser acceptance cannot be certified until executed on an environment permitting Docker/server access. Preparing infrastructure is not evidence that it ran.

### Current dependency decisions

- FastAPI/Uvicorn provide the real HTTP API; SQLAlchemy and Pydantic/settings handle persistence, validation and environment configuration. Python 3.11 is supported because it is locally available; the tested runtime and transitive versions are recorded in `backend/requirements-local.txt`.
- Next.js/React provide App Router pages and the same-origin API proxy. TypeScript, ESLint and Playwright provide static checks and browser journeys. `frontend/package-lock.json` freezes the resolved tree.
- Tailwind was removed from the runnable CRM after its native package could not be obtained in this restricted environment. The frontend uses shared CSS tokens and authored responsive CSS; there is no runtime mock substituting for a missing dependency.
- Compatible-major npm overrides pin available cached versions of parser/Babel/browser-data/accessibility tooling. They were necessary because registry DNS is unavailable and cached metadata pointed to uncached newer tarballs. The resulting frontend still must pass type, lint and production-build checks. This is not a claim that dependency security scanning ran.
- A dependency-free OpenAPI-to-TypeScript generator handles the schema constructs the actual application emits and rejects unsupported constructs. It exports request/schema contracts and an operation map; generic collection response dictionaries are not falsely advertised as fully typed domain records. A maintained full client generator can replace it in a connected environment.
- Redis, asyncpg, Alembic and Celery scaffold is retained only for the future ERP profile; the CRM has no dependency on a running Redis/PostgreSQL service. The current Docker Compose file starts two services with a persistent SQLite volume.

### Current schema and API contract

`orgs`, `users`, `login_sessions` are the identity foundation. CRM tables are `leads`, `contacts`, `parties`, `pipelines`, `stages`, `deals`, `activities`, `campaigns`, `campaign_members`, `tickets`, `ticket_messages`, `deal_stage_history`, `audit_events`, and `crm_idempotency_keys`. All business records carry tenant identity; ordinary CRM records have UUID string IDs, owner, tags, timestamps, soft-delete and version. Lead/deal money is NUMERIC(18,2), serialized as decimal strings. Private attachment metadata lives in `attachments` (migration `0004_attachments.sql`), with random disk keys, SHA-256 content digest, filename, MIME type, byte size, tenant/owner and entity links. Downloads require current access to the linked record. Integration/automation models live in `backend/app/modules/engagement/models.py`; numbered local migrations are the executable schema record.

REST prefix is `/api/v1`. Entity collection GET returns `{items,total,page,page_size}` with `q,status,owner_id,stage_id,limit,offset,sort,order` parameters; create/detail/patch/delete are real endpoints. Additional commands: `/leads/duplicates`, `/leads/{id}/convert`, `/leads/{id}/merge`, `/attachments` (scoped list and raw binary upload), `/attachments/{id}/download`, `/attachments/{id}` (delete), `/deals/{id}/stage`, `/deals/{id}/won`, `/deals/{id}/lost`, `/activities/{id}/complete`, `/tickets/{id}/messages`, `/{entity}/{id}/timeline`, `/{entity}/import`, `/{entity}/export`, `/search`, `/pipelines`, `/dashboard`, `/reports/{name}`. Conversion and create support an Idempotency-Key. Version checks reject stale edits. Optional `GET /demo/status` and Owner/Admin `POST /demo/seed` create clearly labelled fictional records through real services, idempotently. Dashboard `period=all|7d|30d|90d` filters by record creation, not recognized revenue dates. The generated OpenAPI route inventory is available at `/api/v1/openapi.json`.

---

# Future ERP architecture proposal (superseded as immediate scope)

The following original Phase 0 ERP proposal is retained for future planning. Its review-stop instruction and phase sequence no longer control the active CRM implementation. Statements of future architecture, complete schema and statutory compliance below are **planned only**.

# ERP implementation plan

Status: **Phase 0 planning and scaffold only; awaiting the user's review before Phase 1.**

This is a design for the complete requested ERP, not a claim that these features exist. `CHECKLIST.md` is the delivery record. A feature stays unchecked until its UI, API, persistence, security, integration effects and tests satisfy `AGENTS.md`. Phase 0 does not create working business modules or a production account.

## 1. Inspection and scope

The first repository command was `git status --short`. `/Users/apple/Desktop/crm` was empty and was not a Git repository. There was no application, migration history, authentication, UI library, design system or uncommitted code to replace. The requested empty-repository stack therefore applies.

The nearby reference `/Users/apple/Desktop/processpay ` (directory name includes a trailing space) was inspected read-only for CRM ideas. It contains separate FastAPI/SQLAlchemy and Next.js applications, CRM models/services/endpoints, migrations, tests, lead conversion UI, deal boards, contact pages, stale-deal and task views. Useful patterns: a conversion dialog with existing-record selection, a shared record header, table/board alternatives, timeline, next-action visibility and neglected-lead reminders. These concepts inform Phase 2. Its application is not copied: inspected deal monetary fields use `Float`, and a dashboard hook aggregates the first 100 API records with TypeScript checking disabled. Those choices conflict with this specification. No secrets, credentials, customer database, production records or reset scripts are imported. No August Design System is present in the new workspace; design tokens will be established once in Phase 1.

Scope is all mandatory modules through Phase 8, including the later integrations, HR, payroll and AI; optional manufacturing remains an explicit final Phase 7 workstream. Only the Phase 0 review gate stops autonomous phase progression. Provider-dependent functionality remains disabled with setup guidance until real credentials and successful provider validation exist.

## 2. Architecture and module ownership

One modular monolith exposes REST `/api/v1`, with Next.js as its browser client. PostgreSQL is the authoritative database. Redis is the Celery broker and short-lived cache/rate-limit store, never the authority for balances, idempotency or document state. The same application package runs API, worker and Beat processes; these are deployment roles, not microservices. MinIO supplies the local S3 API. PDFs use HTML/CSS rendered by WeasyPrint. The browser uses generated OpenAPI types/client, TanStack Query/Table, react-hook-form/zod and dnd-kit.

| Boundary | Owns and exposes |
| --- | --- |
| `core` | Configuration, DB/session/unit of work, tenancy context, authorization, logging/redaction, safe errors, encryption interfaces. No business-table writes from routers. |
| `platform` | Tenant/company hierarchy, identity/membership, roles, configuration, audit, attachments, notifications, search/views, imports/exports, reusable entity registry. |
| `crm` | Lead/contact/deal lifecycle, activities, campaign/ticket/forecast/communication records. Calls the masters party service to convert a lead. |
| `masters` | Shared parties and addresses, item/catalog/UoM/price/tax/payment-term configuration. A customer and vendor may be the same party. |
| `sales` | Quotations, sales orders, deliveries, sales invoices, receipts and sales credit notes. Requests stock/accounting effects through document events. |
| `purchase` | Requisitions, purchase orders, GRNs, purchase bills, vendor payments and purchase debit notes; matching tolerances. |
| `inventory` | Immutable stock ledger, balances, valuation layers, batches/serials, transfers, adjustments/counts. Sole stock mutation interface. |
| `accounting` | Chart of accounts, immutable journals and allocations, books/periods, bank reconciliation and close. Sole GL posting interface. |
| `gst` | Effective tax policies, statutory snapshots, return preparation, GSP requests/results. Does not file returns or invent registration results. |
| `hr` | Employee/attendance/leave/salary/payroll; salary access restricted independently from general employee access. |
| `manufacturing` | Optional BOM/work order/production/scrap orchestration; inventory and posting remain with their owners. |
| `reports` | Read-only, permission-scoped SQL projections/aggregates; financial reports use posted ledger entries. No authoritative balance writes. |
| `integrations` | Provider adapters, encrypted credentials, connection/sync state, inbound events, payment links, Tally, public API/webhooks. |
| `ai` service inside integrations | One organization-switchable AI gateway for all later AI capabilities, model/provider policy, jobs and human confirmation. |
| `engines` | Reusable document state machine, numbering, GL posting, stock, tax, approval, automation and event infrastructure. Engines call owner interfaces; table ownership does not move into callers. |

Every feature follows `router → service → repository → model`. Services receive a unit of work and caller context; repositories receive the same tenant context. Routers validate and authorize the operation and serialize results, without ORM queries. Engine interfaces are typed and injectable so that tests can exercise real database transactions without a web server. Side effects are durable events, not direct HTTP calls between modules.

### Atomic document processing and durable events

There are two requirements to preserve together: cross-module effects are driven by transactional outbox events processed by Celery, and a successful submitted document must have all stock/GL effects atomically committed. The design uses a durable document operation:

1. An authenticated create/submit/payment request supplies `Idempotency-Key`. The platform reserves the scoped key with a canonical request hash. Reuse with a different payload is `409 IDEMPOTENCY_CONFLICT`; a genuine retry returns the existing result/operation.
2. A submit request locks/checks document version and permissions, records a `document_operations` row plus `DocumentSubmitRequested` in `outbox_events` in one transaction, and returns `202` with an operation URL. The lifecycle remains Draft or Pending Approval while a separately shown operation is queued/processing; it never falsely says Submitted. In-flight documents cannot be edited. Approval eligibility is rechecked at execution time.
3. A Celery handler claims the event and operation, takes document/series/stock/period locks in deterministic order, revalidates authorization and all business rules, and runs the originating module's submit service. It invokes inventory/accounting/masters owner interfaces **sequentially with the same transaction**, not with independent commits. Those interfaces alone write their own tables. The document, number, source allocations, stock ledger and balance, valuation, GL and audit/outbox completion events commit together.
4. On any failure, the transaction rolls back. A separate failure-state transaction records a safe operation error; stock and GL remain unchanged. A worker crash leaves a retryable lease, and operation/source uniqueness prevents duplicate posting. The UI waits/polls or receives an event; success is shown only after commit. Stock conflicts return `STOCK_NOT_AVAILABLE` through the operation with an actionable message.
5. Notifications, email, search indexing, automation and outgoing webhooks consume completion events asynchronously. Each handler records `(org_id, event_id, handler_name)` in its own transaction with its output. Celery is at-least-once; no exactly-once delivery claim is made. Provider calls use their own idempotency keys and reconciliation when outcomes are uncertain.

This is an explicit interpretation of the specification, subject to Phase 0 review. It avoids both non-atomic separate stock/GL commits and bypassing the requested Celery event boundary. Lead conversion, master merge and other multi-table commands use the same operation mechanism when crossing ownership boundaries. Simple single-module draft writes can commit synchronously with an outbox event.

The outbox dispatcher uses leases and `FOR UPDATE SKIP LOCKED`; it records publication attempts and can safely republish. Handler receipts, durable operations and business uniqueness are the correctness controls, not Redis locks. Poison events have bounded exponential backoff/jitter, a visible failed-job state and controlled replay. Aggregate version/order checks stop old events undoing new state. No network call is made while holding stock/GL locks. One SQLAlchemy AsyncSession is used per sequential unit of work and never shared by parallel tasks.

### Tenant, record and field isolation

All business tables, including child rows, have non-null `org_id`. A single base repository applies tenant, soft-delete and record-scope predicates to reads/writes/bulk operations; an opaque ID from another organization returns 404. Caller-supplied `org_id` cannot override authenticated context. Composite `(org_id, id)` unique keys and composite FKs prevent cross-tenant relationships. Company/branch constraints and warehouse ownership are checked within the tenant. User identities are global infrastructure identities; membership, grants, sessions and all personal business data remain tenant scoped. The tenant root `orgs.id` is its own tenant identifier.

Action grants and own/team/branch/all scopes are evaluated before object existence is disclosed. Field policies apply to response schemas, searches, filters, sorting, aggregates, exports, notifications, audit rendering and AI context; hiding a table cell is insufficient. Salary is limited to HR/Owner, even if another role has ordinary employee access. PostgreSQL RLS may provide defense in depth later; repository isolation remains the mandatory single application enforcement boundary. Background jobs rehydrate explicit tenant and actor/service permission contexts, with no unrestricted repository fallback.

### Quantities, money, dates and concurrency

Money is `NUMERIC(18,2)`, quantity `NUMERIC(18,3)`, rates `NUMERIC(18,4)` and probabilities/rates bounded decimals. Python Decimal does the arithmetic; API decimal values are strings. The browser preview uses decimal arithmetic and is replaced with the server result. Monetary line rounding and document round-off are explicit, versioned rules, recorded with the submitted tax snapshot and Round-Off ledger. Overflow, invalid precision, zero/negative prohibited quantities and mixed-currency misuse are validation errors.

UTC timestamps use `timestamptz`; business posting/due dates use `date`. Each organization defaults to Asia/Kolkata and an April–March financial year. Accounting-period boundaries are derived in the company's configured business timezone. Indian/grouped number formatting is a user/organization preference; exports carry unambiguous numeric data.

Version checks protect drafts and stage changes. Submit locks the document and source quantities; numbering locks the relevant series; stock locks balances and FIFO layers in sorted item/warehouse/batch order. Creating a missing balance first uses a unique-key-safe insert then locks the row. Negative stock fails unless explicitly enabled. When enabled, provisional costing and subsequent valuation adjustments are represented as new entries, never overwrites. Deadlock/serialization retries are bounded and retain the same idempotency key. Period locks and fiscal close use a company-period guard shared by posting and locking operations so a concurrent close cannot race a post.

## 3. Data model

The following is the complete target schema, not a Phase 0 migration. Tables are added with new migrations as their phases are implemented. All business tables inherit **B**: `id UUID PK`, `org_id UUID NOT NULL`, `created_at`, `updated_at`, `created_by`, `updated_by`; master records additionally have `deleted_at`. Actor IDs may be null for bootstrap/system jobs with a recorded service actor. Posted documents and immutable history never permit delete; immutable rows keep creation/update metadata equal. Master deletes are soft deletes and cannot erase references.

Every business table has a tenant index and `UNIQUE(org_id,id)` for composite relationships. All FK columns use a tenant-prefixed index unless already covered by a composite index below. In the tables below, `U(...)` is a tenant-prefixed unique index; `I(...)` is a tenant-prefixed btree index. Name/email/normalized-phone search gets pg_trgm GIN indexes combined with tenant predicates; `custom_fields JSONB` gets GIN plus promoted expression indexes for frequently used typed fields. Partial active-master uniqueness uses `WHERE deleted_at IS NULL`. Historical references remain valid after archival. JSONB stores bounded structured configuration/snapshots, not substitutes for financial relational facts.

### 3.1 Platform and shared engines

| Tables | Key columns and relations | Important indexes / constraints |
| --- | --- | --- |
| `orgs` | name, slug, timezone, number_format, plan_state, ai_enabled; root tenant | unique slug; id is tenant ID |
| `companies` | name, legal_name, PAN, base_currency, fiscal_year_start_month, valuation_method, perpetual_inventory | U(PAN) where appropriate; configurable accounting policy version |
| `branches` | company_id, code, state_code, GSTIN, registration_type, address, letterhead_attachment_id | U(company_id,code), GSTIN validation; I(GSTIN) |
| `warehouses` | branch_id, code, name, active | U(branch_id,code) |
| `users` | global normalized_email, password_hash, name, timezone, active, email_verified_at | unique normalized_email; identity table is explicit non-business tenant exception |
| `org_members` | user_id, default_branch_id, active, invited_by | U(user_id), I(active,user_id) |
| `roles` | name, description, built_in, active | U(name) |
| `role_permissions` | role_id, module, action, visibility_scope, field_rules | U(role_id,module,action) |
| `member_roles`, `member_branches` | org_member_id with role_id / branch_id | U(each pair); prevent privilege assignment outside actor's authority |
| `teams`, `team_members` | team name, manager_member_id; team_id, org_member_id | U(team name); U(team_id,org_member_id) |
| `invites` | normalized_email, token_hash, roles, branches, expires_at, accepted_at, revoked_at | unique token_hash; I(normalized_email,expires_at) |
| `refresh_tokens` | member_id, session_id, family_id, token_hash, expires_at, revoked_at, replaced_by_id, last_seen_at, device_label | unique hash; I(member_id,revoked_at); rotate/reuse detection |
| `password_reset_tokens`, `email_verification_tokens` | user_id, token_hash, expiry, consumed_at | unique hash; I(user_id,expiry); identity-system exception with intended tenant recorded when available |
| `oauth_identities`, `mfa_factors`, `mfa_recovery_codes` | user_id, provider subject / encrypted TOTP secret / recovery hash; verified_at, revoked_at | unique(provider,subject), one-time recovery codes; Phase 7 |
| `settings` | scope_type, scope_id, namespace, key, typed_value, version | U(scope_type,scope_id,namespace,key) |
| `numbering_series` | company_id, branch_id, fiscal_year_id, document_type, prefix, next_number, padding, max_length | U(branch_id,fiscal_year_id,document_type,prefix); row lock; length check |
| `document_registry` | entity_type, entity_id, company_id, branch_id, status, number, fiscal_year_id | U(entity_type,entity_id); statutory U(company/GST registration,FY,number) namespace to avoid colliding branch series |
| `document_operations` | operation_type, document_id/type, requested_by, expected_version, state, result, safe_error, lease_until, idempotency_id | I(state,lease_until); one active submit/cancel operation per document |
| `document_links`, `document_line_allocations` | from/to document registry IDs, relationship; source_line_type/id, target_line_type/id, quantity, allocation_kind, reversal_of_id | U(source,target,kind); I(source line,kind); pending qty locked on conversion/submit |
| `document_tax_lines` | document_id, line_id, component, taxable_amount, rate, tax_amount, ledger_id, rule_version, place_of_supply | I(document_id,line_id); immutable submitted snapshot |
| `idempotency_keys` | member/API identity, method, route, key, request_hash, state, response/operation pointer, expires_at | U(identity,method,route,key); financial source uniqueness survives expiry |
| `custom_field_definitions` | entity_type, key, label, type, constraints/options, permissions, active, version | U(entity_type,key); values in entity `custom_fields` |
| `saved_views` | entity_type, owner_id, visibility, filter_ast, sorts, columns, version | I(entity_type,owner_id,visibility); permission validate referenced fields |
| `recently_viewed` | member_id, entity_type, entity_id, viewed_at | U(member_id,entity_type,entity_id); I(member_id,viewed_at) |
| `attachments` | entity_type/id, bucket_key, filename, MIME, bytes, sha256, scan_state, uploaded_by | unique bucket_key; I(entity_type,entity_id); authorized download and quarantine |
| `notifications` | recipient_id, event_id, kind, entity_type/id, title, read_at, channel, delivery_state | U(recipient_id,event_id,kind,channel); I(recipient_id,read_at,created_at) |
| `notification_preferences` | member_id, event_kind, in_app, email, reminder_offset | U(member_id,event_kind) |
| `audit_logs` | actor_id/service_actor, action, entity_type/id, field_path, redacted_old/new, request_id, event_id | I(entity_type,entity_id,created_at), I(actor_id,created_at); append-only |
| `import_jobs`, `import_errors` | entity_type, attachment_id, mapping, dedupe_mode, state, totals/progress, error_attachment_id; job_id, row_number, field, code, safe_message | I(state,created_at); U(job_id,row_number,field,code) |
| `import_row_results`, `export_jobs` | job_id,row_number,hash,result_entity_id; entity_type, filter/column snapshot, format, state, result_attachment_id | U(job_id,row_number); I(actor,state); retry checkpoint |
| `automation_rules` | name, trigger_type, condition_ast, action_ast, enabled, validated_version, max_depth | I(trigger_type,enabled); allowlisted operators/actions |
| `automation_runs`, `automation_action_runs` | rule_id, event_id, root_event_id, depth, state, attempts, safe_error; run_id, action_index, result | U(rule_id,event_id); U(run_id,action_index); I(state,next_retry_at) |
| `approval_rules` | document_type, branch_id, condition_ast, approver_role_id, threshold, priority, active, version | I(document_type,branch_id,active,priority) |
| `approval_requests`, `approval_decisions` | document_id, rule_version, state, requested_by, snapshot_hash; request_id, approver_id, decision, comments, decided_at | I(state,approver role); immutable decisions; edited document invalidates approval |
| `outbox_events` | aggregate_type/id/version, event_type, payload, schema_version, occurred_at, publish_state, attempt, next_attempt_at, lease_until, root_event_id | U(aggregate_type,id,version,event_type); partial I(publish_state,next_attempt_at) |
| `event_handler_receipts` | event_id, handler_name, processed_at, result_reference | U(event_id,handler_name) |
| `integrations` | provider, company/branch scope, encrypted_credentials, key_version, status, validated_at, settings, disconnected_at | U(provider,scope); no credentials in ordinary responses |
| `api_keys` | member/service identity, name, key_hash, prefix, grants, scopes, expiry, revoked_at | unique key_hash; I(prefix); secret displayed once |
| `webhooks`, `webhook_deliveries` | URL, encrypted_secret, subscribed_events, enabled; webhook_id, event_id, signature_version, attempt, status, response_code, retry_at | U(webhook_id,event_id); I(status,retry_at); SSRF validation |
| `consent_records`, `privacy_requests`, `retention_policies` | person entity, purpose, source, granted/revoked_at; subject, request_type, verification/state, job_id; record_class, legal_basis, retention_until | I(entity_type,entity_id,purpose); I(state,created_at); no financial hard-delete shortcut |
| `public_forms`, `public_form_submissions` | schema, entity_type, allowed_fields, captcha configuration, active; form_id, request_fingerprint, source, result_id | I(form_id,created_at); provider token/replay controls |

### 3.2 CRM

| Tables | Key columns and relations | Important indexes / constraints |
| --- | --- | --- |
| `leads` | name, normalized_email, phone_e164, company_name, job_title, website, industry, company_size, city/state, source_id, campaign_id, status_id, rating, score, owner_id, team_id, branch_id, estimated_value, budget, timeline, next_follow_up_at, first_response_at, converted_contact/party/deal_id, converted_at, custom_fields, version | I(owner_id,status_id,next_follow_up_at), I(team_id,status_id), I(phone_e164), I(normalized_email); duplicate warning not global rejection |
| `lead_statuses`, `lead_sources` | code/name, position, system_meaning, active | U(code); configurable defaults |
| `lead_conversions`, `record_merges` | lead_id, contact_id, party_id, deal_id, operation_id; entity_type, survivor_id, merged_id, preserved_history_snapshot | U(lead_id); U(entity_type,merged_id); exactly one conversion result |
| `contacts` | name, designation, party_id, owner_id, team/branch_id, consent_summary, communication_preferences, custom_fields | I(party_id), I(owner_id,name) |
| `contact_emails`, `contact_phones` | contact_id, normalized_email / phone_e164, label, primary | U(contact_id,value); partial unique primary per contact; searchable values |
| `pipelines`, `stages` | pipeline name/default; pipeline_id,name,position,probability,required_fields,category(open/won/lost),stale_after_days | U(name); U(pipeline_id,position), bounded probability |
| `deals` | name, party_id, primary_contact_id, pipeline_id, stage_id, amount, currency, probability, owner/team/branch, expected_close_date, stage_entered_at, close_reason_id/text, won/lost_at, forecast_category, custom_fields, version | I(owner_id,stage_id,expected_close_date), I(pipeline_id,stage_id); closed deals excluded from open metrics |
| `deal_contacts` | deal_id, contact_id, relationship, primary | U(deal_id,contact_id) |
| `deal_stage_history` | deal_id, from/to_stage_id, actor_id, changed_at, amount/probability snapshot, reason | I(deal_id,changed_at); immutable |
| `lost_reasons`, `assignment_rules` | reason label, active; lead conditions, method(round_robin/state/source), candidate_member_ids, cursor, priority, active | I(active,priority); locked round-robin cursor |
| `activity_types`, `activities` | configurable kind; entity_type/id, kind, subject, body, owner/assignee, start/end/due, completion_at, outcome, recurrence_id, reminder_at, timezone | I(assignee_id,status,due_at), I(entity_type,entity_id,created_at) |
| `activity_recurrences`, `activity_reminders` | rule, timezone, next_occurrence_at, end_at; activity_id,recipient_id,offset,scheduled_at,state | U(recurrence_id,occurrence_start) on generated activities; U(activity_id,recipient_id,offset) |
| `mentions`, `tags`, `entity_tags` | activity/note_id, member_id; name,color; tag_id,entity_type/id | U(note_id,member_id), U(tag name), U(tag_id,entity_type,entity_id) |
| `campaigns`, `campaign_members` | name,type,budget,actual_cost,start/end,owner_id; campaign_id,lead/contact/party reference, attribution_weight,source_event | I(start_date,end_date); U(campaign_id,entity_type,entity_id) |
| `campaign_costs`, `campaign_attributions` | campaign_id,posted_journal_line_id,amount; campaign_id,deal/invoice line,weight,model,source | unique cost/source references; revenue only from real posted outcomes |
| `tickets` | number, party/contact_id, subject, priority, status, category_id, assignee/team, sla_policy_id, response_due/resolution_due, first_response_at,resolved_at,escalation_level | U(number), I(status,priority,response_due_at), I(assignee_id,status) |
| `ticket_categories`, `sla_policies`, `ticket_sla_events` | names; priority/calendar/response/resolution targets, version; ticket_id,event_type,time,pause_duration | I(ticket_id,created_at); effective policy snapshot |
| `ticket_messages` | ticket_id,author_id,body,visibility(internal/customer),channel,provider_message_id | I(ticket_id,created_at); provider unique where present; internal never exposed to public |
| `sales_targets`, `forecast_snapshots`, `forecast_snapshot_lines` | owner/team/pipeline,period,target; captured_at,period,scope; snapshot_id,deal_id,amount,probability,category,expected_close | U(scope,period), I(period,captured_at); U(snapshot_id,deal_id) |
| `email_templates`, `email_messages` | name,subject,body,allowed_merge_fields; entity_type/id,template_id,recipients,provider_id,status,accepted/sent/delivered/bounced_at,reply_to_id | U(template name); unique(provider,provider_id), I(entity_type,entity_id,created_at) |
| `email_delivery_events`, `communication_preferences` | message_id,provider_event_id,status,event_at; person entity,channel,purpose,consent_record_id,opt_out | unique(provider,provider_event_id); U(person,channel,purpose) |

### 3.3 Masters

| Tables | Key columns and relations | Important indexes / constraints |
| --- | --- | --- |
| `parties` | code,name,legal_name,is_customer,is_vendor,parent_party_id,GSTIN,PAN,registration_type,state_code,credit_limit,credit_policy,payment_terms_id,price_list_id,owner/team/branch,health,renewal_date,custom_fields | U(code), I(GSTIN), I(PAN), I(parent_party_id), I(owner_id,name); one or both role flags |
| `party_addresses` | party_id,type,lines,city,state_code,pincode,country,primary | I(party_id,type); one primary per address type |
| `party_contacts` | party_id,contact_id,role,primary | U(party_id,contact_id); partial primary uniqueness |
| `items` | SKU,name,goods/service,HSN_SAC,item_group_id,brand_id,base_uom_id,tax_category_id,sales/purchase_rate,batch/serial flags,reorder_level,valuation_override,default_warehouse_id,barcode,custom_fields | U(SKU), U(barcode) where set; I(item_group_id,name); valuation override must comply with company policy |
| `item_groups`, `brands` | name,parent_group_id / name | U(name); group cycle check |
| `uoms`, `uom_conversions` | code,name,precision; item_id(optional),from_uom_id,to_uom_id,numerator,denominator | U(code); U(item scope,from,to); positive exact conversion factors |
| `price_lists`, `item_prices`, `discount_rules` | name,currency,buy/sell,validity; price_list_id,item_id,uom_id,rate,min_qty,validity; scope,conditions,discount type/value,priority,validity | I(item_id,price_list_id,valid_from); no overlapping conflicting effective rules |
| `tax_rates`, `tax_templates`, `tax_template_lines` | component,rate,effective_from/to,HSN/category; name,jurisdiction; template_id,tax_rate_id,ledger_id,order,calculation_basis | I(category,effective_from), U(template_id,component,order) |
| `tax_categories`, `state_tax_jurisdictions` | HSN/SAC/category,description; state_code,name,UT legislature flag,effective dates | versioned reference data; U(code,effective_from) |
| `payment_terms`, `payment_term_lines` | name; terms_id,days,percentage,anchor | U(name); percentages total 100 |
| `batches`, `serial_numbers` (inventory owner) | item_id,batch_no,manufactured_at,expires_at; item_id,serial_no,batch_id,state,current_warehouse_id | U(item_id,batch_no), U(item_id,serial_no); I(item_id,expires_at); serial warehouse is derived/validated against movements |
| `item_attributes`, `item_attribute_values`, `item_variants` (later) | attribute name/type; attribute_id,value; parent_item_id,child_item_id,combination_hash | U(parent_item_id,combination_hash); child remains ordinary stocked item |

Party opening balances are posted accounting opening vouchers with party dimensions, never a manually mutable balance field. Revenue/account health summaries are derived from authorized data with explicit as-of time.

### 3.4 Shared business-document header and lines

Every document header **D** adds to B: `company_id`, `branch_id`, `fiscal_year_id`, `document_number`, `posting_date`, `document_date`, `status`, `version`, `party_id` where relevant, `currency`, `exchange_rate`, `net_total`, `tax_total`, `round_off`, `grand_total`, `due_date`, `terms_snapshot`, `address/GSTIN/place_of_supply_snapshot`, `submitted_by/at`, `cancelled_by/at`, `cancellation_reason`, `amended_from_id`, `custom_fields`. It has `I(branch_id,status,posting_date)`, `I(party_id,posting_date)` and U(number namespace,FY,document_number). Draft UUIDs are not tax invoice numbers.

Every document line **L** adds to B: `parent_id`, `position`, `item_id`, `description_snapshot`, `HSN_SAC_snapshot`, `quantity`, `uom_id`, `base_quantity`, `conversion_snapshot`, `rate`, `discount_type/value/amount`, `tax_template_id`, `taxable_amount`, `tax_amount`, `line_total`, `warehouse_id`, `batch_id`, and `source_line_reference`. U(parent_id,position); I(item_id,parent_id). Per-line allocations reference true source lines. Serial allocations use `document_line_serials(line_type,line_id,serial_id,quantity)` with unique source allocation checks. Documents snapshot mutable master descriptions/tax/address/terms so later master edits do not change historical PDFs.

| Tables | Header/line additions and relations | Important constraints |
| --- | --- | --- |
| `quotations`, `quotation_items` | D/L; validity, deal_id | expired quotation conversion policy |
| `sales_orders`, `sales_order_items` | D/L; quotation references,promised_date; ordered/delivered/billed projections | projections reconciled from active line allocations |
| `delivery_notes`, `delivery_note_items` | D/L; ship_to,carrier,dispatch_date,SO line allocations | stock issues exactly once per source line |
| `sales_invoices`, `sales_invoice_items` | D/L; invoice_kind,reverse_charge,export/SEZ treatment,e_invoice_state; linked deliveries or direct stock flag | direct invoice must not repeat an earlier delivery stock issue |
| `receipts`, `receipt_items` | D; party_id,bank/cash account,amount,mode,reference,advance flag; component/tender details | receipt allocation <= confirmed posted receipt value |
| `payment_allocations` | payment_type/id, invoice_type/id,amount,allocation_date,journal_line refs,reversal_of_id | I(invoice_type,id), I(payment_type,id); row locks prevent over-allocation |
| `credit_notes`, `credit_note_items` | D/L; original invoice,line refs,reason,return_stock,return_warehouse | returned qty/value <= original less prior returns; financial-only credit explicitly supported |
| `purchase_requisitions`, `purchase_requisition_items` | D/L; requested_by,required_date,cost_centre_id | no vendor mandatory until sourcing |
| `purchase_orders`, `purchase_order_items` | D/L; requisition allocations,expected_date,approval snapshot | value approval; source quantity conservation |
| `goods_receipts`, `goods_receipt_items` | D/L; PO allocations,received/accepted/rejected quantities,warehouse | immutable received cost provisional until bill variance |
| `purchase_bills`, `purchase_bill_items` | D/L; supplier_invoice_no/date,GRN/PO allocations,reverse_charge,input_credit_category,matching_status | U(party_id,supplier_invoice_no,supplier FY) active posted; deviations require disposition |
| `vendor_payments`, `vendor_payment_items` | D; vendor_id,bank/cash account,amount,advance flag,reference; tender/withholding components | allocation ledger shared with receipts |
| `debit_notes`, `debit_note_items` | D/L; original bill,line refs,reason,return_stock | return valuation references original receipt layers |
| `three_way_match_results` | purchase_bill_id,line_id,PO/GRN quantities/rates,variances,tolerance_version,disposition,approved_by | U(bill line,match version); append-only resolution history |
| `payment_schedules` | invoice_type/id,due_date,amount,terms_line_id,journal_open_item_id | I(due_date,invoice_type,id) |

### 3.5 Inventory

| Tables | Key columns and relations | Important indexes / constraints |
| --- | --- | --- |
| `stock_ledger_entries` | item_id,warehouse_id,batch_id,qty_in/out,rate,value,posting_date,sequence,voucher_type,voucher_id,voucher_line_id,reversal_of_id,valuation_method | I(item_id,warehouse_id,posting_date,sequence); unique(source line,effect index); immutable; one movement direction |
| `stock_balances` | item_id,warehouse_id,batch_id,on_hand_qty,reserved_qty,total_value,average_rate,version,last_entry_id | U(item_id,warehouse_id,batch_id) with nulls not distinct; locked atomic update |
| `stock_cost_layers`, `stock_layer_consumptions` | receipt_entry_id,remaining_qty,remaining_value; issue_entry_id,layer_id,quantity,value,reversal_of_id | I(item_id,warehouse_id,receipt_date,sequence); U(issue_entry_id,layer_id,effect index) |
| `stock_serial_movements`, `stock_reservations` | entry_id,serial_id,from/to warehouse; sales_order_line,item/warehouse/batch,quantity,expires_at,state | unique(entry_id,serial_id); I(serial_id,created_at); I(item_id,warehouse_id,state) |
| `stock_transfers`, `stock_transfer_items` | D/L; from/to warehouses,transfer_mode,received_at | paired issue/receipt entries; in-transit warehouse for two-step transfer |
| `stock_adjustments`, `stock_adjustment_items` | D/L; reason,approval_id,offset_account_id | mandatory reason/approval policy |
| `stock_counts`, `stock_count_items` | D/L; counted_at,balance_snapshot,actual_qty,variance,freeze/cutoff | variance posts through adjustment service; concurrent movement cutoff handled |
| `stock_valuation_adjustments`, `stock_reorder_rules` | source_bill/return,affected_entry,value_delta,GL ref; item/warehouse,min_qty,reorder_qty,lead_days | unique(source,effect); U(item_id,warehouse_id) |

The stock ledger is the truth; balances and layers are transactionally maintained projections with reconciliation tests. Moving average is default. FIFO consumes oldest eligible layers deterministically. Returns reverse original cost allocations rather than current selling price. GRN/bill price differences adjust remaining inventory and already-expensed COGS through new stock value/GL entries. Backdated stock writes trigger ordered recalculation using appended adjustment entries within an unlocked period; closed-period historical entries are not edited. Expired-batch issue rules and unique serial transitions are validated at submit.

### 3.6 Accounting and GST

| Tables | Key columns and relations | Important indexes / constraints |
| --- | --- | --- |
| `account_groups`, `accounts` | company_id,name,parent_id,root_category,normal_balance; group_id,code,name,type,party_required,active | U(company_id,code), I(group_id); no cycles; used accounts archived not deleted |
| `fiscal_years`, `period_locks` | company_id,label,start/end,state; fiscal_year_id,start/end,locked_by,reason,version | U(company_id,start_date), nonoverlapping periods |
| `journal_entries` | company_id,branch_id,posting_date,status,voucher_type/id,description,total_debit/credit,reversal_of_id,posting_version | unique(source,effect index); I(company_id,posting_date,status); immutable after posting |
| `journal_lines` | entry_id,position,account_id,debit,credit,party_id,cost_centre_id,branch_id,due_date,currency,base_amount,voucher_type,voucher_id,voucher_line_id | U(entry_id,position), I(account_id,posting_date), I(party_id,due_date); debit XOR credit; source required |
| `journal_open_items`, `journal_settlements` | journal_line_id,party_id,due_date,original_amount; debit_line_id,credit_line_id,amount,settlement_date,reversal_of_id | U(journal_line_id); I(party_id,due_date); settlement totals cannot exceed open amounts |
| `cost_centres`, `opening_balance_batches`, `fiscal_close_runs` | company_id,code,parent_id; company/FY,date,state,journal ref; FY,state,closing_journal_id,checksum | U(company_id,code), U(FY,close version); no unbalanced opening batch |
| `bank_accounts`, `bank_statement_lines`, `bank_matches` | company_id,account_id,encrypted account details,IFSC; bank_account_id,external_id,date,description,amount,balance,import_job_id,fingerprint; statement_line_id,journal_line_id,amount,state,matched_by | U(bank_account_id,fingerprint), I(bank_account_id,date), U(statement line,journal line); split match sum validation |
| `voucher_documents`, `voucher_document_items` | D/L for journal/payment/receipt/contra/debit/credit voucher UI; account/debit/credit/cost centre/party line dimensions | document submit calls same posting engine; no second GL path |
| `gst_document_snapshots`, `gst_line_snapshots` | source document,registration,return period,supply/category,place_of_supply,recipient GSTIN,reverse_charge,zero_rate_reason; HSN,taxable value,components,ITC eligibility | unique(source,posting version); I(registration,period,category); immutable including reversals |
| `gst_return_runs`, `gst_return_run_lines` | company/branch GSTIN,period,form,schema_version,state,artifact_id,source_checksum; run_id,snapshot_id,section,amounts | I(registration,period,form); export reproducibility, no filed state without provider evidence |
| `statutory_rule_versions`, `tds_tcs_sections`, `withholding_entries` | jurisdiction,rule,validity,source_url,verified_by/date; section,rate,threshold,validity; source_document,party,section,taxable/tax_amount,journal_line | effective-date indexes; all statutory implementation marked `# VERIFY-WITH-CA` |
| `e_invoice_requests`, `eway_bill_requests` | source_document,integration_id,request_hash,state,provider_request_id,IRN/QR or bill_no,acknowledged_at,safe_error,cancellation_ref | U(source,request_hash); provider identifiers only from verified responses |

Deferred database checks/triggers enforce journal balance at posting/commit, supported by engine Decimal validation and tests. A draft journal may be incomplete; a posted journal cannot be. GL lines always identify voucher type/id and carry the dimensions needed for trial balance, P&L, balance sheet, cash flow, general/day/party/cash/bank books, AR/AP aging and DSO/DPO without reading document tables. Open-item/settlement records link ledger lines; payment allocation UI records are not a parallel source of financial truth. Cash-flow mappings live on account/report configuration. All financial reports exclude drafts and include posted reversals.

### 3.7 HR, manufacturing, integrations and AI

| Tables | Key columns and relations | Important indexes / constraints |
| --- | --- | --- |
| `employees`, `departments`, `designations` | employee_code,member_id,company/branch,department/designation,joining/leaving dates,encrypted bank/PAN,manager_id; name,parent/manager; name,grade | U(employee_code), I(department_id,active); salary not in ordinary employee response |
| `attendance`, `leave_types`, `leave_applications` | employee_id,date,check_in/out,status,source; name,paid,accrual policy; employee_id,type_id,from/to,days,status,approval_id | U(employee_id,date), I(employee_id,from_date,status) |
| `leave_balances`, `leave_ledger_entries`, `holidays` | employee_id,type_id,period,available; employee/type,date,delta,source; company/branch,date,name | U(employee,type,period); append-only leave movements; U(scope,date,name) |
| `salary_components`, `salary_structures`, `salary_structure_components` | code,earning/deduction,formula,statutory_rule_id; name,validity; structure_id,component_id,formula/value,sequence | U(code), U(structure_id,component_id); safe expression evaluator |
| `employee_salary_assignments`, `payroll_statutory_rates` | employee_id,structure_id,validity,base_amount; state,section,rate/threshold,validity | no overlapping assignment; I(state,section,effective_from) |
| `payroll_runs`, `payslips`, `payslip_lines` | company,period,branch,state,approval_id,journal_entry_id; run_id,employee_id,gross/deductions/net,PDF attachment; payslip_id,component_id,amount,formula_snapshot | U(company,period,run kind), U(run_id,employee_id); immutable approved payroll |
| `boms`, `bom_items`, `work_orders` | output_item,version,output_qty,validity; BOM,component,qty,UoM,scrap%; D, BOM version,qty,planned dates | U(output_item,version); BOM cycle check; frozen work-order BOM |
| `material_issues`, `material_issue_items`, `production_entries`, `production_entry_items`, `scrap_entries` | D/L,work_order_id,source warehouse; D/L,consumed layers,produced qty,rolled_cost; work_order/item/qty,recovery value,warehouse | unique stock/GL effect sources; raw/finished cost reconciliation |
| `integration_sync_runs`, `integration_object_links`, `integration_webhook_events` | integration_id,direction,cursor,state,counts,errors; provider_object_type/id,local_type/id,version; provider_event_id,payload_hash,verified_at,state | U(integration_id,provider object), U(provider,event_id); I(state,retry_at) |
| `mail_sync_cursors`, `calendar_events`, `whatsapp_messages` | integration/mailbox,cursor; external_id,activity_id,start/end,sync version; person/entity,template/provider_id,status | unique provider IDs; consent enforcement; no invented delivery states |
| `payment_links`, `payment_provider_events` | invoice_id,provider_id,amount,currency,expiry,state; verified event ID,link_id,payment_id,amount,status | unique provider event/payment IDs; webhook matching cannot overpay twice |
| `connector_jobs`, `connector_job_items` | integration_id,Tally/import/export kind,mapping_version,state,artifact; job_id,row/source_id,result/errors | U(job_id,source_id); external XML parsed safely |
| `ai_jobs`, `ai_outputs`, `entity_embeddings` | member_id,task_type,entity_type/id,provider/model,state,consent policy,usage; job_id,structured_output,review_state,confirmed_by; entity_type/id,content_hash,embedding,model_version | I(state,created_at), U(entity,model version); vector index only in Phase 7 |
| `bill_extractions` | attachment_id,ai_job_id,structured_draft,confidence,confirmed_by,created_purchase_bill_id | one confirmed draft conversion; never auto-post |
| `report_jobs`, `dashboard_preferences` | report_name,filters,actor,as_of,state,artifact_id; member_id,role,layout,date_compare | I(actor,state), U(member_id,role); cache keys include full permission context |

Polymorphic links use `entity_type + entity_id` from an allowlisted entity registry. Because SQL cannot FK arbitrary table names, a central entity-reference validator and lifecycle checks verify tenant/existence/visibility before creating such links; high-value document references use `document_registry` FKs. Merge transactions retarget allowed links, preserve immutable history and leave a survivor redirect, never rewrite posted financial identities.

## 4. Document and operational flows

**Lifecycle:** Draft → Pending Approval when rules match → Submitted → Cancelled. Rejection returns an editable draft with comments/history. Approved content hash/version must match the document being submitted. Pending jobs are operation state, not a fabricated lifecycle state. Submitted documents are locked. Cancel generates compensating stock/GL/tax entries in one owner-service transaction and keeps the number permanently allocated. Amend is cancel plus a new linked draft; it gets a new number when submitted. Downstream dependencies must be cancelled/reversed in reverse order or resolved by a return/credit workflow. Cancellation into locked periods follows an explicitly dated, permitted reversal procedure; it never silently changes the original date.

**Lead to cash:** lead → atomic contact + customer party + deal (or authorized existing records) → quotation → SO → partial delivery → partial invoice → part/full receipt. The conversion result is uniquely keyed by lead. Source-line allocations distinguish delivered and billed quantities; conversion copies only remaining eligible quantities. Services and direct invoices skip physical delivery when appropriate; a direct stocked invoice owns its single stock issue. Sales invoice posts Dr customer / Cr sales / Cr output GST, with round-off as needed. Delivery posts Dr COGS / Cr stock. Receipt posts Dr cash/bank / Cr customer; advances remain an identifiable credit/open item until allocated. Credit control reads ledger exposure plus defined commitments under locks and applies configured warn/block policy. Customer statement and aging are ledger reports.

**Procure to pay:** requisition → approved PO → partial GRN → purchase bill → vendor payment. GRN increases stock and posts Dr stock / Cr goods-received-not-invoiced clearing under perpetual inventory. The bill clears GRNI and records input GST/vendor liability; quantity/rate differences create an explicit match exception and valuation/expense adjustment. A service/non-stock bill posts expense/purchase plus input GST against vendor. This avoids debiting inventory both at GRN and bill. Vendor advances remain ledger open credits/debits until applied. PO/GRN/bill matching uses versioned tolerances, with mandatory review outside limits.

**Returns:** a physical sales return credits receivable/tax/revenue and receives stock at original issue cost (Dr stock / Cr COGS); a financial-only credit note has no stock movement. A purchase return debits vendor and reverses input tax plus original inventory/expense effects. Return quantities cannot exceed eligible originals. Unlinked returns need explicit authorization and documented costing.

**Inventory:** opening/GRN/production receive; delivery/material issue dispatch; returns reverse; transfer creates linked issue and receipt with value conservation; approved adjustment/count variance creates an auditable movement and offset GL. Stock balances/valuation always reconcile to ledger movements. Batch expiry and serial uniqueness operate on base UoM quantities. Stock valuation reports disclose as-of dates and pending backdate adjustments.

**GST:** calculate taxable line amount from server quantity/rate/discount and effective HSN/SAC data. Compare supplier branch state with the legally determined place of supply, not blindly the address; same-state CGST+SGST or applicable UTGST, otherwise IGST. Preserve goods/services place-of-supply rule and evidence. Export/SEZ is zero-rated with explicit LUT/bond or legally applicable paid-tax route and SEZ eligibility; do not equate every zero-rated transaction to a hardcoded 0% line. Capture B2B/B2C, unregistered, reverse charge and ITC eligibility. Return preparation uses submitted/reversal snapshots reconciled to GL and registers; JSON format versions are validated against current GST portal tooling. GSP e-invoice/e-way requests are asynchronous, show provider-confirmed identifiers only and have real cancellation/status reconciliation.

**Approvals and automations:** a shared condition AST evaluates typed authorized fields. Approval stages/roles, no-self-approval policy where configured, comments and audit all persist. Automation validates triggers/conditions/actions before activation; durable per-action idempotency, depth/root-event tracking and bounded retry stop loops and duplicate emails/tasks. Event handlers cannot bypass the same permission/service validation as users.

**Imports:** stage CSV/XLSX, map/preview/validate, then process each row in a transaction/savepoint so failures do not leave partial contacts/addresses. Persist row outcomes to resume safely. Skip/update/create dedupe policy is explicit. A 1,000-row import with 20 invalid rows must finish 980 successful rows plus a downloadable protected error file. Formula-injection protection applies to CSV/XLSX exports. Exports snapshot filters/columns and recheck access when executed/downloaded.

**Bank and payroll:** bank statement import deduplicates source rows; suggestions require user confirmation before reconciliation, supporting split matches. Payroll snapshots effective salary/statutory formulas and attendance/leave, awaits approval, produces real PDFs and one balanced payroll journal; reruns cannot post twice.

## 5. REST API catalogue

All routes below are `/api/v1`. Requests validate through Pydantic v2; generated OpenAPI is the contract. Typed client generation is CI checked. Decimal values are JSON strings; timestamps ISO-8601 UTC; cursor responses are `{items, next_cursor, has_more}` with bounded limits and optional aggregate count. Filter input is an allowlisted typed AND/OR AST with bounded complexity. Stable sort includes an ID tie-breaker. Unsupported/invisible filter/sort fields are rejected rather than leaked. Bulk jobs have explicit atomicity/row-results contracts.

For each ordinary master/record collection: `GET /{entity}` (search/filter/sort/cursor), `POST /{entity}`, `GET /{entity}/{id}`, `PATCH /{entity}/{id}` (version/If-Match), `DELETE /{entity}/{id}` (authorized soft delete), `POST /{entity}/bulk`, `POST /{entity}/import`, `GET /{entity}/export`. Immutable histories, ledger entries and posted documents intentionally reject generic PATCH/DELETE with a safe domain error; their list/detail/export is available, while business writes use owner command routes. Each feature UI shows only implemented, permitted actions.

| Area | Collections and commands |
| --- | --- |
| Identity | `POST /auth/signup`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/logout-all`, `/auth/password-reset/request`, `/auth/password-reset/confirm`, `/auth/email/verify`; `GET /auth/sessions`; `DELETE /auth/sessions/{id}`; later `/auth/google/start`, `/auth/google/callback`, `/auth/mfa/enrol`, `/verify`, `/disable`, `/recovery-codes` |
| Membership/hierarchy | `/companies`, `/branches`, `/warehouses`, `/members`, `/roles`, `/teams`, `/invites`; `POST /invites/{token}/accept`, `/members/{id}/deactivate`; role action/scope/field grants; branch switch validates membership |
| User platform | `GET/PATCH /me`, `GET /me/tasks`, `GET/PATCH /me/preferences`, `/settings`, `/numbering-series`, `/custom-fields`, `/saved-views`, `/recently-viewed`, `/notifications`, `/notification-preferences`; `POST /notifications/{id}/read`, `/notifications/read-all`; `GET /search?q=...` |
| Audit/files/jobs | `GET /audit-logs`; `POST /attachments/upload`, `GET /attachments/{id}/download`; `GET /jobs/{id}`, `/jobs/{id}/errors`; `POST /jobs/{id}/retry`; `GET /operations/{id}` with safe persisted outcome |
| CRM core | `/leads`, `/contacts`, `/deals`, `/pipelines`, `/stages`, `/lead-statuses`, `/lead-sources`, `/lost-reasons`, `/assignment-rules`; `POST /leads/{id}/convert`; `GET /leads/duplicates`; `POST /{entity}/merge`; `PATCH /deals/{id}/stage`; `POST /deals/{id}/won`, `/lost`; `GET /deals/{id}/history` |
| Activities | `/activities`, `/activity-types`, `/tags`; `POST /activities/{id}/complete`, `/activities/{id}/reschedule`; `GET /calendar?from=&to=&view=`; `/recurrences`; `POST /{entity}/{id}/mentions` |
| CRM advanced | `/campaigns`, `/campaigns/{id}/members`, `/tickets`, `/tickets/{id}/messages`, `/sla-policies`, `/sales-targets`, `/forecast-snapshots`; `POST /tickets/{id}/reply`, `/tickets/{id}/escalate`; `GET /forecast`; `POST /forecast-snapshots/capture` |
| Communication | `/email-templates`, `/email-messages`; `POST /email-messages/{id}/send`; `GET /email-messages/{id}/status`; `POST /calls/log`; consent-aware email/WhatsApp send routes; `/communication-preferences` |
| Masters | `/parties`, `/party-addresses`, `/party-contacts`, `/items`, `/item-groups`, `/brands`, `/uoms`, `/uom-conversions`, `/price-lists`, `/item-prices`, `/discount-rules`, `/tax-rates`, `/tax-templates`, `/payment-terms`, `/batches`, `/serial-numbers`; `POST /parties/validate-gstin`; `POST /prices/preview` |
| Sales documents | `/quotations`, `/sales-orders`, `/delivery-notes`, `/sales-invoices`, `/receipts`, `/credit-notes`; `/payment-allocations`; `GET /parties/{id}/statement`; `POST /receipts/{id}/allocate`, `/allocations/{id}/reverse` |
| Purchase documents | `/purchase-requisitions`, `/purchase-orders`, `/goods-receipts`, `/purchase-bills`, `/vendor-payments`, `/debit-notes`; `GET /purchase-bills/{id}/match`; `POST /purchase-bills/{id}/match/resolve`, `/vendor-payments/{id}/allocate` |
| Shared document commands | For each document: `POST /{doc}/{id}/submit`, `/cancel`, `/amend`, `/convert?to=...`; `GET /{doc}/{id}/pdf`, `/links`, `/history`; `POST /{doc}/{id}/email`, `/preview-totals`; create/submit/payment/convert require idempotency |
| Inventory | read-only `/stock-ledger-entries`, `/stock-balances`; documents `/stock-transfers`, `/stock-adjustments`, `/stock-counts`; `POST /stock/opening`, `/stock-counts/{id}/post-variance`; `/stock-reorder-rules`; reservation/release commands |
| Accounting | `/account-groups`, `/accounts`, `/cost-centres`, `/fiscal-years`, `/period-locks`, `/bank-accounts`; draft `/journal-entries` and `/vouchers`; immutable `/journal-lines`; `POST /periods/{id}/lock`, `/unlock`, `/fiscal-years/{id}/close`, `/opening-balances/import`; `POST /bank-statements/import`; `GET /bank-statement-lines/{id}/suggestions`; `POST /bank-matches`, `/bank-matches/{id}/reverse` |
| Governance | `/approval-rules`, `/approval-requests`, `/automation-rules`; `POST /approval-requests/{id}/approve`, `/reject`; `POST /automation-rules/{id}/validate`, `/enable`, `/disable`; `GET /automation-runs`; privacy request/export/anonymize routes with retention review |
| Reports | `GET /dashboard/{role}`; `GET /reports/{name}` and `/reports/{name}/export?format=csv|xlsx|pdf`; financial: trial-balance, profit-loss, balance-sheet, cash-flow, general-ledger, day-book, party-ledger, cash-bank-book, ar-aging, ap-aging, dso-dpo; CRM funnel/sources/win-loss/rep/forecast; sales/purchase registers; inventory balance/valuation/movement/aging/slow-moving/reorder; support-SLA |
| GST | `GET /reports/gst/hsn`, `/gstr-1`, `/gstr-3b`, `/itc`; `POST /gst/returns/prepare`; `GET /gst/returns/{id}/export`; `POST /sales-invoices/{id}/e-invoice`, `/e-invoice/cancel`, `/eway-bill`; `GET /gst/provider-requests/{id}` |
| Integrations/public | `/integrations`; `POST /integrations/{id}/validate`, `/connect`, `/disconnect`, `/sync`; `GET /integrations/{id}/sync-runs`; `/api-keys`, `/webhooks`; `POST /public/forms/{id}/submit` (captcha+rate limit); `POST /webhooks/{provider}` (signature+replay validation); `POST /sales-invoices/{id}/payment-link`; Tally connector jobs |
| HR | `/employees`, `/departments`, `/designations`, `/attendance`, `/leave-types`, `/leave-applications`, `/holidays`, `/salary-components`, `/salary-structures`, `/payroll-runs`; `POST /leave-applications/{id}/approve`, `/reject`; `POST /payroll-runs/{id}/calculate`, `/approve`, `/submit`; `GET /payslips/{id}/pdf` |
| Manufacturing | `/boms`, `/work-orders`, `/material-issues`, `/production-entries`, `/scrap-entries`; BOM explode/cost preview and document commands |
| AI | `POST /ai/search`, `/ai/email-draft`, `/ai/call-summary`, `/ai/deal-risk`, `/ai/lead-score`, `/ai/duplicates`, `/ai/bill-extraction`; `GET /ai/jobs/{id}`; `POST /ai/bill-extractions/{id}/confirm`; per-org disable stops new provider calls |

Errors always use `{ "error": { "code": "STOCK_NOT_AVAILABLE", "message": "Only 1 unit is available in this warehouse.", "details": {} } }`. Field errors identify safe field paths. Authentication failures are 401, denied actions 403, hidden/not-found records 404, stale/version/idempotency/business conflicts 409, validated-input failures 422, throttles 429; no SQL, stack trace, tokens or secrets in responses. Public provider webhook routes use provider signatures rather than cookie CSRF, with raw body verification before parsing. Cookie-authenticated mutations require CSRF protection and Origin validation.

## 6. Frontend and UX plan

Phase 1 establishes semantic tokens for color, typography, spacing, density, radii, elevation and focus; a professional icon set; and accessible shadcn primitives. ProcessPay is inspiration for CRM work organization, not a code or data dependency. No logo/font is borrowed without an intentional local asset decision.

The shell has a collapsible module sidebar, authorized company/branch switcher, Ctrl+K search, quick-create, notifications and profile. Navigation is derived from implemented routes plus backend grants. Core shared components: cursor table/query filter builder, column/saved-view controls, bulk actions, searchable select, decimal/date input, form errors, custom-field renderer, record header/timeline/related/history tabs, linked document chain, approval panel, document status/operation display, PDF preview and attachment manager.

Tables perform server search/filter/sort/pagination and never aggregate a downloaded page as the total business metric. Record pages support authorized inline edits with optimistic version conflict handling. Forms provide required markers, inline validation, loading submits and unsaved-change warning. Document grids support Tab navigation, Enter to add a row, item lookup by name/SKU/barcode, live decimal previews and tax breakup with final server validation. Deal Kanban sends stage commands and reverts on validation/permission/version errors. Every screen designs loading, empty, error, permission denied, validation, success, long text and large-data behavior before acceptance.

Mobile sales/store flows retain essential controls without hiding errors. Focus/contrast/keyboard/screen-reader checks accompany accessibility review. Phone values produce valid `tel:` and `wa.me` links. Print CSS has a white background, company letterhead and GST invoice content. Dashboards provide date comparison and a records/report drill-through for every metric; no data means a clear empty state. Permission-aware query keys include organization/company/branch/user context and are cleared on identity/scope change. Heavy modules and report editors load on demand.

## 7. Security, operations and performance

JWT access/rotating refresh cookies are HttpOnly, Secure in production and scoped SameSite with CSRF/Origin controls. Argon2 hashes passwords; reset/invite/session secrets are stored as hashes and consumed once. Logout-all/session revocation and user deactivation take effect on API and worker commands. Auth/public/API-key routes are rate limited. Permissions default to deny, with editable role templates (Owner, Admin, Accountant, Sales Manager, Sales Rep, Purchase, Store Keeper, Support Agent, HR, Read-only/CA). API keys have scoped grants and expiration independent of UI roles.

Integration tokens/secrets are envelope-encrypted with key versioning and rotation guidance. Logs are structured JSON with request/trace IDs and explicit redaction of tokens/passwords/phone/email/PAN/bank/salary. Sentry is opt-in and receives scrubbed contexts. Attachments are size/MIME/content checked, quarantined before download and stored under opaque keys. Download authorization is rechecked before short-lived URLs. Rendered email/user HTML is sanitized; PDF rendering blocks unapproved remote/local resource fetching; webhooks defend against private-network SSRF; spreadsheet exports neutralize formulas. Safe parsers, parameterized SQL and typed filters prohibit user-supplied SQL/formula execution.

Consent records store source/purpose/time. Privacy requests require subject verification, person-data export and audit; lawful retention/anonymization rules preserve financial facts. Statutory retention periods and DPDP commencement dates are effective configuration verified against current official rules before production; the application does not promise deletion that would destroy required ledgers.

Performance target: representative permission-scoped list endpoints with 100,000 records per org have p95 server response below 500 ms on a documented local/CI-like hardware profile after warmup, excluding network and explicitly heavy export jobs. Benchmark filters, joins, cursor traversal and tenant skew; record query plans and query counts to catch N+1. Tenant+owner/status/date/party/item/warehouse indexes, trigram search and JSONB GIN are baseline; profile before extra indexes/caching. Heavy exports/imports/PDFs/reports use workers and progress. Report caches include permissions and as-of/version and never cross tenants.

Compose runs PostgreSQL 16 with extensions, Redis, MinIO, API, worker, Beat and frontend; a migration one-shot dependency runs before application readiness. A fresh environment needs no external credentials for core operation. Readiness verifies actual dependencies/migration state; liveness only process viability. Production guide covers TLS, backups/PITR, object retention, restores, secret rotation, non-root containers, resource limits, migrations/rollback and worker/outbox monitoring. Development credentials are clearly local-only; no default production admin.

## 8. Folder structure

```text
backend/
  app/
    main.py
    core/                 config, db, security, tenancy, permissions, logging, errors
    engines/              documents, numbering, posting, stock, tax, approvals, automation, events
    modules/
      platform/ crm/ masters/ sales/ purchase/ inventory/ accounting/
      gst/ hr/ manufacturing/ reports/ integrations/
        models.py schemas.py repository.py service.py router.py tests/
    workers/              Celery app, outbox dispatcher, task registry
  migrations/             Alembic env + append-only versions
  tests/                  contract, integration, isolation, concurrency, engines
  pyproject.toml
  Dockerfile
frontend/
  src/
    app/                  App Router routes
    components/ui/        shared primitives
    components/shared/    table, forms, records, document grid, app shell
    features/<module>/
    lib/api/              generated OpenAPI client/types
    hooks/
  tests/                  Playwright main journeys and accessibility checks
  package.json tsconfig.json Dockerfile
infra/                    database image/extension bootstrap, deployment helpers
scripts/                  seed, OpenAPI generation, verification, load seed
docs/                     setup, operations, integration setup, statutory review notes
.github/workflows/         CI
docker-compose.yml .env.example
PLAN.md CHECKLIST.md AGENTS.md CHANGELOG.md README.md
```

Phase 0 may use empty module packages to reserve boundaries, but they do not count as completed module implementations. Generated clients are generated artifacts and updated from the backend contract, never separately invented interfaces.

## 9. Phases and acceptance gates

| Phase | Deliverables | Required evidence before completion |
| --- | --- | --- |
| 0 | Repository/reference inspection, this plan, exhaustive checklist, agent rules; minimal Docker/CI/migration/backend/frontend skeleton | Actual scaffold checks reported; missing tooling/network blockers recorded; **STOP for user's review** |
| 1 | Auth/tenancy/hierarchy/RBAC/settings/numbering/audit/files/notifications, app shell/shared components, import/export/search infrastructure | Signup/invite/login, sessions, tenant 404/own scope, field access, idempotency, migration and fresh-compose smoke tests |
| 2 | CRM leads/contacts/customer parties/deals/pipelines/activities/My Day/calendar/saved views/dashboard | Conversion transaction+replay, phone duplicate warning, history+audit on stage drag, closed exclusion, 1,000/20 import, real aggregate dashboard |
| 3 | Items/UoM/pricing/tax configuration/CoA/posting/journals/stock+valuation/opening/trial balance | Decimal/tax engine vectors, balanced/immutable journals, stock concurrency+FIFO/average, opening ledger reconciliation |
| 4 | Sales/purchase/GST transactions, payments/allocations/returns/matching/PDF | Full partial order-to-cash and procure-to-pay; same/interstate hand calculations; double submit; last-unit race; cancel/reversal/number retention |
| 5 | Statements/GST/bank/approvals/automations/custom fields/role dashboards/period locks/close | Financial reconciliation, GSTR-1/register equality, PO approval, field-safe reports, locked-period race, automation loops/retries, DB-matched metrics |
| 6 | Campaign attribution/support SLA/forecast/email/WhatsApp | Real provider status or correctly disabled connector; SLA/calendar/forecast scenarios, consent/internal-note protection |
| 7 | Gmail/Outlook/calendar/payment/GSP/Tally/public API+webhooks; Google/2FA; item variants; TDS/TCS; HR/payroll; optional manufacturing; AI | Provider sandbox evidence when credentials exist; idempotent signed events; salary isolation, approved payroll journal, manufacturing cost conservation, AI off switch and bill confirmation |
| 8 | Security/load/accessibility/responsive audits, complete docs/deployment/restore guide, final seed and fresh-clone verification | All engine/API/E2E/isolation/concurrency/import/automation checks, lint/type checks, 100k load evidence, full compose startup and restore drill |

At each phase end, run applicable acceptance checks from `CHECKLIST.md`; fix failures before progressing. Record command/results and update `CHANGELOG.md`. Skipped/manual/provider-dependent checks are named as gaps, not passed. The final end-to-end demo seed is idempotent, fake and explicitly opt-in, with one company/two different-state branches, parties/items/opening stock, all deal stages, activities/tickets and full submitted document journeys. Empty database onboarding is tested separately. Load data is separate from demonstration data. Fake GSTIN examples satisfy format/checksum for tests but are not asserted to be registrations of real businesses.

## 10. Decisions

1. **Review boundary:** implement only the requested Phase 0 skeleton now. The large remaining product is planned, not silently marked complete. User approval is required before Phase 1 because the specification explicitly requires it.
2. **Stack:** the destination was empty, so use Python 3.12/FastAPI/SQLAlchemy 2 async/Alembic/Pydantic 2; PostgreSQL 16; Redis/Celery/Beat; Next.js App Router/strict TS/Tailwind/shadcn/TanStack/RHF/zod/dnd-kit; WeasyPrint; MinIO/S3; Docker Compose. Pin actual installable versions and commit lockfiles when dependency resolution is available. Do not infer compatibility from latest labels.
3. **Reference reuse:** ProcessPay is read-only UX inspiration. Recreate useful interactions against this system's own typed contract/Decimal/tenant repositories rather than transplanting unsafe arithmetic, limited-page metrics or disabled type checking. No existing working application in the destination was replaced.
4. **Atomicity and outbox:** durable submit operations processed through Celery run owning services in a single DB transaction, with eventual noncritical event consumers. A queued operation is not successful submission. This decision reconciles the spec's outbox mandate and accounting/stock atomicity and is deliberately highlighted for review.
5. **Master identity:** users are global identity records; business membership and sessions carry tenant context. Every business table is tenant scoped, including child/history records. Parties combine customer/vendor roles. Contact/party conversion can link existing records, under locks and unique conversion keys.
6. **Document identity:** drafts use UUIDs; final numbers allocate at successful submit, are unique in the proper legal/FY namespace, and never reused after cancellation. Prefix/padding length is validated before a series can issue a number; GST length <=16. Branch series cannot collide for a shared GST registration.
7. **Ledger authority:** balances, dashboards and open-item status are derived/reconcilable; no editable balance shortcut. Financial reports are GL-only. Stock ledger and GL are immutable and corrections append reversals/adjustments. GRNI clearing avoids double inventory capitalization.
8. **Precision:** Decimal/string API and exact UoM conversion factors; server final calculations. Currency/rate/qty precision follows the specification. INR/base-currency operations first; explicit currency/exchange-rate snapshots allow configured currencies without pretending that FX revaluation/consolidation is implemented.
9. **Compliance:** effective-dated tax/state/statutory tables; `# VERIFY-WITH-CA` on statutory code; CA review record and source/version before live statutory use. Zero-rated does not automatically mean every route has zero payable tax. GST portal export version and GSP schemas must be rechecked during implementation. No return filing is promised.
10. **Later scope:** Google sign-in, 2FA, item variants, TDS/TCS, external mail/calendar, AI and payroll stay explicit in Phase 7. Manufacturing is optional but retained as a named unchecked workstream; it will not be silently deleted.
11. **External status:** credentials absent means disabled/not configured. SMTP acceptance is recorded as accepted, not proof of recipient delivery; delivery requires provider evidence. Payment confirmation comes from verified provider callbacks/reconciliation or an authorized explicitly recorded manual receipt, never a clicked button. AI output is a draft until user confirmation.
12. **Security/privacy:** field access applies everywhere data can escape; signed URLs do not replace authorization; per-purpose consent and retention/anonymization are designed from the start. Statutory dates/retention need current source validation, not hardcoded assumptions.
13. **Seed:** no seeded production admin; production signup is real. Development seed is opt-in, fake and idempotent, uses service/engine pathways for financial facts and is clearly labeled.
14. **Phase verification:** no test is described as passed without an actual successful run. Network/tooling limitations leave relevant checks unchecked with commands to retry. No business acceptance is claimed for scaffold health tests.

### Dependency rationale register

Dependencies named in the user's stack are authorized by the stack decision above. They are installed by phase when used. Any additional package must be added here before adoption, with the lockfile changed in the same phase.

| Dependency / tool | Why needed / adoption phase |
| --- | --- |
| `uvicorn` | ASGI server for FastAPI, Phase 0 |
| `asyncpg` | Async PostgreSQL driver for the mandated SQLAlchemy async stack, Phase 0 |
| `psycopg[binary]` if used by migration tooling | Synchronous PostgreSQL access for migration/admin commands; use only if the chosen migration environment needs it, Phase 0 |
| `pydantic-settings` | Validated environment configuration without printing secrets, Phase 0 |
| `redis` Python client | Redis health checks and Celery integration, Phase 0 |
| `boto3` | S3-compatible object storage boundary and MinIO access, Phase 0/1 |
| `PyJWT`, `argon2-cffi`, `cryptography` | Signed JWTs, required Argon2 passwords and authenticated credential encryption, Phase 1 |
| `email-validator`, `phonenumbers` | Validated email and canonical E.164 normalization including +91 default, Phase 1/2 |
| `python-multipart`, `openpyxl` | Controlled upload parsing and Excel import/export, Phase 1 |
| `jinja2` | Escaped HTML PDF/email templates, Phase 4 |
| `@hey-api/openapi-ts` or `openapi-typescript` (choose one) | Generated browser contract from OpenAPI; final generator must match actual scaffold setup, Phase 0/1 |
| `decimal.js` or equivalent exact-decimal package (choose one) | Non-authoritative but precision-safe browser total previews, Phase 3/4 |
| `lucide-react` | Consistent professional icons with accessible labels, Phase 1 |
| `@hookform/resolvers` | Connect zod to the required react-hook-form stack, Phase 1 |
| shadcn-required Radix/CVA/clsx/tailwind-merge utilities | Accessible primitives and consistent token class composition, Phase 1; record exact packages when components are installed |
| `pytest-asyncio`, `asgi-lifespan`, `anyio` as needed | Async HTTP/database lifecycle testing around pytest/httpx, Phase 0/1 |
| `coverage`/`pytest-cov` | Measure engine coverage and locate omissions, Phase 1 |
| Playwright axe integration | Automated accessibility checks supplementing manual keyboard/screen-reader review, Phase 8 |
| `pgvector` extension/client | Later duplicate embeddings and semantic search; disabled until AI work, Phase 7 |
| Sentry SDK | Opt-in scrubbed error reporting, Phase 8 |

## 11. Official research references

Research checked 2026-10-09. These sources inform the design; they do not constitute a CA sign-off or prove implementation. Relevant versions and official schemas are rechecked in the phase that consumes them.

- [SQLAlchemy 2.0 asynchronous sessions](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html): sessions are transaction state and are not shared across concurrent tasks; supports the sequential unit-of-work choice.
- [Celery task guidance](https://docs.celeryq.dev/en/stable/userguide/tasks.html): idempotent handlers and acknowledgement behavior motivate durable event receipts and replay-safe business keys.
- [PostgreSQL 16 concurrency control](https://www.postgresql.org/docs/16/mvcc.html) and [application consistency checks](https://www.postgresql.org/docs/16/applevel-consistency.html): explicit locks and retry design for stock, numbering and period guards.
- [CBIC CGST rules consolidated text](https://cbic-gst.gov.in/pdf/15102020_CGST-Rules-2017-Part-A-Rules.pdf): Rule 46's invoice numbering and mandatory particulars are the baseline; this older consolidated PDF must be checked against amendments/current CBIC text before Phase 4 delivery.
- [CBIC IGST zero-rated supply, Section 16](https://taxinformation.cbic.gov.in/content-page/explore-act/1000624/1000001/section%2016/ACTS): export/SEZ treatment and eligibility are more nuanced than substituting a generic 0% tax rate.
- [CBIC intra-state supply provisions](https://taxinformation.cbic.gov.in/content-page/explore-act/1000616/1000001): tax split depends on legally determined place of supply and exceptions.
- [GST portal GSTR-1 guide](https://tutorial.gst.gov.in/userguide/returns/GSTR_1.htm) and [returns offline tool documentation](https://tutorial.gst.gov.in/downloads/invoiceuploadofflineutility.pdf): export format/tool compatibility requires current validation rather than hand-invented JSON.
- [MeitY DPDP Rules 2025 notification](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf) and [Act commencement notification](https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf): later rules and phased commencement must be included in privacy implementation review, rather than relying only on the 2023 Act title.

Phase 0 execution results, current setup commands and unresolved tooling limits belong in `README.md`/`CHANGELOG.md` and the end-of-session report, with incomplete checks retained in `CHECKLIST.md`.


## Decisions — landing and navigation review, 2026-10-12

- Public `/` is Relay's product landing page; `/dashboard` is the workspace and auth entry. Signup links use `/dashboard?signup=1` and continue to respect the server's signup setting. Existing entity URLs and `/invite` remain supported.
- Keep the existing green/cream/Georgia visual system. Landing illustrations explain the workflow and are explicitly labelled; they do not invent product metrics or customer endorsements. Gmail remains honestly deferred.
- The root layout owns the persistent CRM shell across workspace routes. Request scopes and effect cleanup prevent an old section or record response from populating a new route; loading is distinct from real empty data.
- A shared custom Select uses a keyboard-operated, viewport-positioned listbox plus a hidden native select for real FormData and constraint validation. All previous visible native selects are migrated. No new dependency or migration.
- Build verification uses an isolated copy with real copied dependencies, preserving the user-started dev server's `.next`. An initial symlinked dependency copy compiled but failed standalone trace placement; a real dependency copy built successfully.
- Visual detector flagged two uses of Arial; intentionally retained to match the existing workspace body type. Fresh independent screenshot review found a static tab-panel focus omission, fixed with tabIndex and vertical tablist semantics. Design-system sidecar metadata was not rewritten.
