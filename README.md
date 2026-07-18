# SkillFlow AI v2 — Backend

A FastAPI backend for tracking fresher onboarding roadmaps and progress reports. **This backend performs no AI generation** — all AI agents (roadmap generation, work evaluation, Q&A, and daily/weekly/final report generation) live in the frontend dashboards. The backend's job is to authenticate users, enforce role and ownership access control, and store and serve whatever AI-generated results the frontend submits.

## Scope (v2)

v2 narrows the product to two roles only:

- **Fresher** — owns a profile, a versioned roadmap, and daily/weekly/final reports.
- **PM (Project Manager)** — views the freshers assigned to them, their roadmap progress, and their reports via a dashboard.

The earlier experienced-employee flow and all backend-side AI generation have been **removed** — the codebase now contains only the active fresher/PM API.

## Technology

- Python 3.9+
- FastAPI
- SQLAlchemy (SQLite)
- Pydantic v2
- Auth: PyJWT (HS256 bearer tokens) + bcrypt password hashing
- Pytest for tests

## Project structure

```
app/
  api/          # Route modules: auth, freshers, pm, demo, health + deps (auth guards)
  models/       # SQLAlchemy models (domain.py)
  schemas/      # Pydantic request/response schemas (auth_schemas.py, v2_schemas.py)
  services/     # Business logic (auth_service.py, report_service.py)
  seed/         # Idempotent demo seeder (seed_v2.py)
  config.py     # Settings (reads .env)
  database.py   # SQLAlchemy engine/session setup
  main.py       # FastAPI app entrypoint
tests/          # Pytest suite (33 tests)
scripts/
  run_local.sh    # Create venv, install deps, start the server
  reset_demo.sh   # Call POST /api/demo/reset and pretty-print the result
```

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   cd "/Users/ios/Documents/Workspace/Team Arcens/backend"
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create your local environment file:

   ```bash
   cp .env.example .env
   ```

   Or skip both steps and just run `./scripts/run_local.sh` (below) — it creates the venv, installs dependencies, and copies `.env.example` to `.env` automatically if one doesn't exist yet.

## Start & stop

**Start (recommended):**

```bash
cd "/Users/ios/Documents/Workspace/Team Arcens/backend" && ./scripts/run_local.sh
```

This creates the venv if missing, installs dependencies, ensures `.env` exists, and starts uvicorn on `http://10.0.128.20:8000` with auto-reload.

**Start (manual alternative):**

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Stop:** press `Ctrl+C` in the terminal running the server.

## Demo reset

Reset the database back to its seeded demo state via the helper script:

```bash
./scripts/reset_demo.sh
```

or by calling the endpoint directly:

```bash
curl -X POST http://10.0.128.20:8000/api/demo/reset
```

The reset is **idempotent** — calling it repeatedly re-establishes the same seeded accounts without creating duplicates.

## Seeded credentials

Both accounts use the password `Demo@123`.

| Role    | Email                       | User ID     | Name         |
|---------|------------------------------|-------------|--------------|
| Fresher | `fresher@skillflow.local`    | `USR-F001`  | Aarav Patel  |
| PM      | `pm@skillflow.local`         | `USR-PM001` | Priya Menon  |

The seeded fresher (Aarav Patel) is assigned to the seeded PM (Priya Menon), and the fresher gets an **empty** profile row. **No sample roadmaps, tasks, or reports are seeded** — the dashboard and API return only the real data your frontend submits. This keeps the demo free of placeholder content and avoids hardcoding any department/role.

## Authentication

Auth uses JWT bearer tokens (HS256).

1. Obtain a token:

   ```bash
   curl -X POST http://10.0.128.20:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "fresher@skillflow.local", "password": "Demo@123"}'
   ```

   Response: `{ "access_token": "...", "token_type": "bearer", "user": {...} }`

2. Send it on subsequent requests:

   ```bash
   curl http://10.0.128.20:8000/api/auth/me \
     -H "Authorization: Bearer <access_token>"
   ```

Token expiry is configurable via the `JWT_EXPIRY_MINUTES` environment variable in `.env` (default `720` minutes / 12 hours).

## Running tests

```bash
cd "/Users/ios/Documents/Workspace/Team Arcens/backend"
source .venv/bin/activate
python -m pytest tests/ -v
```

All 33 tests pass.

## API docs

Interactive Swagger UI is available at:

```
http://10.0.128.20:8000/docs
```

## Database

- SQLite file: `skillflow.db` in the backend root, created automatically on first startup.
- `POST /api/demo/reset` (or `./scripts/reset_demo.sh`) safely recreates the demo dataset (seeded users, profile, roadmap, and daily report) without duplicating accounts, so it's safe to run before every demo or QA pass.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Port 8000 already in use | Another process is bound to the port. Free it with `lsof -ti:8000 \| xargs kill`, then restart. |
| `401 Unauthorized` | The request is missing an `Authorization: Bearer <token>` header, or the token is invalid/expired. Log in again via `POST /api/auth/login`. |
| `403 Forbidden` | The authenticated user's role doesn't match the endpoint (e.g. a fresher hitting a `/api/pm/*` route), or a PM is requesting a fresher who isn't assigned to them. |
| `ModuleNotFoundError` / import errors on startup | The virtual environment isn't activated. Run `source .venv/bin/activate` before starting uvicorn, or use `./scripts/run_local.sh`, which handles this automatically. |

## No AI dependency

This backend requires **no AI or OpenAI API key** to run and performs **no AI generation** of any kind — there are no AI/LLM packages in `requirements.txt`. All roadmap content, evaluations, Q&A, and reports are generated by the frontend and submitted to this backend purely for storage, access control, and retrieval.
