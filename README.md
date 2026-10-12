<div align="center">

# relay.

**A simple, honest CRM for B2B sales and support teams.**

Leads, contacts, companies, deals, follow-ups and support tickets — all in one connected workspace.

![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![SQLite](https://img.shields.io/badge/SQLite-persistent-003B57?logo=sqlite&logoColor=white)

![Relay CRM landing page](docs/screenshots/landing.png)

</div>

---

## ⚡ Quick start

You need **Python 3.11 or 3.12** (or [uv](https://docs.astral.sh/uv/)) and **Node.js 22+**.

```sh
git clone https://github.com/terabhaicoder/relay-crm.git
cd relay-crm
python3 scripts/dev.py
```

That is all. On the first run, the script:

1. creates `backend/.venv` and installs the Python packages,
2. runs `npm ci` in `frontend/`,
3. starts the API and the web app together.

| What | Where |
| --- | --- |
| 🖥️ Web app | http://127.0.0.1:3007 |
| ⚙️ API | http://127.0.0.1:8010 |
| 📘 API docs (Swagger) | http://127.0.0.1:8010/api/v1/docs |

Open the web app and **sign up** to create your own workspace. No external accounts or API keys are needed. Press `Ctrl+C` to stop both servers.

> **Tip:** Use `python3 scripts/dev.py --port 4000 --api-port 9000` to change ports, or set `CRM_PYTHON` to use a Python you have already prepared.

---

## ✨ What you can do

| Area | Features |
| --- | --- |
| 🎯 **Leads** | Capture leads, find and merge duplicates (with a same-phone warning), qualify, and convert into a linked contact + company + deal in one step. Converting twice never creates duplicates. |
| 📊 **Pipeline** | Kanban board and table views, drag deals between stages, multiple pipelines, stage history, required loss reasons. Won/lost deals stay out of open-pipeline totals. |
| ✅ **My Day & Tasks** | Tasks, calls, meetings and notes linked to customer records, plus a calendar view. |
| 🎧 **Support** | Tickets linked to company/contact/deal. Internal notes are kept separate from customer reply drafts. |
| ⚡ **Automations** | Rules that turn lead/deal/ticket events into tasks and notifications. Retried events never run the action twice. |
| 📥 **Import / Export** | CSV import with row-level checks, deduplication and a downloadable error file. Exports are protected from spreadsheet-formula injection. |
| 📎 **Attachments** | PDF, image, text and CSV files on records (10 MB limit) with permission-checked downloads. |
| ✉️ **Email workspace** | Templates and drafts. Gmail is shown as *not connected* — nothing is ever marked "sent" unless it really was. |
| 👥 **Team & roles** | Invitations, roles, read-only users, and own-record visibility for sales reps. Each workspace is fully isolated — another workspace's record ID returns 404. |
| 📈 **Reports** | Dashboard numbers come straight from the database. Indian number format (₹1,00,000 / ₹5.2 L / ₹1.3 Cr). |

---

## 🧱 Tech stack

```
┌──────────────────────────┐        ┌───────────────────────────┐        ┌────────────┐
│  Next.js 16 · React 19   │  HTTP  │  FastAPI · SQLAlchemy 2   │  SQL   │   SQLite   │
│  TypeScript (typed API)  │ ─────▶ │  routers → services →     │ ─────▶ │ backend/   │
│  frontend/  :3007        │        │  repositories → models    │        │  erp.db    │
└──────────────────────────┘        │  backend/  :8010          │        └────────────┘
                                    └───────────────────────────┘
```

- **Backend:** FastAPI, SQLAlchemy 2, Pydantic 2. Numbered SQL migrations run on startup, with checksums.
- **Frontend:** Next.js App Router with a TypeScript client generated from the OpenAPI schema.
- **Database:** a real, persistent SQLite file (`backend/erp.db`). Startup never wipes existing data.
- **Safety built in:** real session auth, tenant scoping in one shared repository layer, server-side validation, `Idempotency-Key` on create endpoints, and exact decimal money.

### Project layout

```
relay-crm/
├── backend/            FastAPI app, migrations and tests
│   ├── app/
│   ├── local_migrations/
│   └── tests/
├── frontend/           Next.js web app and Playwright tests
│   └── src/
├── scripts/dev.py      One-command local start (sets everything up on first run)
├── docs/               Deployment guide, demo script, startup notes
└── docker-compose.yml  Container setup
```

---

## 🎬 Try sample data

New workspaces start empty. You can either use the **sample data** button inside the app (all records are clearly marked as fictional), or create a demo owner at startup:

```sh
DEMO_SEED=true DEMO_PASSWORD='choose-a-password' python3 scripts/dev.py
```

The demo login email is `owner@demo.local` unless you set `DEMO_EMAIL`. Never turn on demo data in production.

A five-minute walkthrough is in [docs/HACKATHON_DEMO.md](docs/HACKATHON_DEMO.md).

---

## 🐳 Docker

```sh
docker compose --env-file .env.example up --build
```

This runs the web app and the API. Data is kept in the `crm_data` volume. For a production setup with HTTPS, backups and rollback, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## 🧪 Tests and checks

```sh
# Backend
cd backend
uv sync
uv run pytest -m 'not integration'
uv run ruff check . && uv run mypy app

# Frontend
cd ../frontend
npm run lint
npm run typecheck
npm run build
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3007 npm run test:e2e
```

Backend tests run the real API against temporary SQLite databases — no mocks. See [CHECKLIST.md](CHECKLIST.md) and [CHANGELOG.md](CHANGELOG.md) for the exact checks that have been run and what is still open.

---

## 🛠️ Manual setup (if you prefer)

```sh
python3.11 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-local.txt
(cd frontend && npm ci)
python3 scripts/dev.py
```

**Common issues**

- *"Python 3.11 or 3.12 is required"* — install one of them, or install `uv` and run again.
- *Python packages failed to install* — delete `backend/.venv` and run `python3 scripts/dev.py` again.
- *Port already in use* — pass `--port` and `--api-port`.

---

## 🗺️ Roadmap

- Gmail / Google Calendar sync through real OAuth
- PostgreSQL + Redis/Celery for multi-instance scale
- ERP modules (accounting, inventory, GST, payroll) — planned in [PLAN.md](PLAN.md), **not built yet**

