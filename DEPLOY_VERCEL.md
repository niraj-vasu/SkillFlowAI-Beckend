# Deploying SkillFlow AI backend to Vercel (+ Vercel Postgres)

This backend is ready for Vercel. It runs as a serverless function and uses **Vercel Postgres**
(SQLite is only for local dev — it cannot persist on Vercel).

## What's already prepared in the code
- `api/index.py` — the serverless entrypoint (exposes the FastAPI `app`).
- `vercel.json` — routes **all** paths (`/health`, `/api/*`, `/docs`, `/verify`) to the function.
- `app/database.py` — auto-detects the DB: uses `DATABASE_URL` or Vercel's `POSTGRES_URL`,
  and rewrites `postgres://…` to the `postgresql+psycopg://` driver. Falls back to SQLite locally.
- `requirements.txt` — includes `psycopg[binary]` (the Postgres driver).
- Tables are created and demo accounts seeded automatically on the first request (idempotent).

## One-time setup (things only you can do)

### 1. Make sure this folder is in your Git repo
Vercel deploys from Git. If the backend is a **subfolder** of your repo, note its path
(e.g. `backend/`) — you'll set it as the Root Directory in step 2.

Commit and push these new/changed files:
`api/index.py`, `vercel.json`, `requirements.txt`, `app/database.py`, `app/main.py`.

### 2. Create the Vercel project
1. Vercel dashboard → **Add New… → Project** → import your Git repo.
2. If the backend is in a subfolder: **Root Directory → `backend`** (or wherever this folder is).
3. Framework preset: **Other** (leave build/output settings empty — `vercel.json` handles it).
4. Don't deploy yet — add the database first (step 3).

### 3. Add Vercel Postgres
1. In the project → **Storage → Create Database → Postgres** → create it.
2. **Connect it to this project.** Vercel automatically injects the connection env vars
   (`POSTGRES_URL`, etc.) into the project — the app reads `POSTGRES_URL` with no extra config.

### 4. Set environment variables
Project → **Settings → Environment Variables** (Production + Preview):

| Name          | Value                                  | Notes |
|---------------|----------------------------------------|-------|
| `JWT_SECRET`  | a long random string                   | **Required** — don't ship the dev default. e.g. `openssl rand -hex 32` |
| `CORS_ORIGINS`| `*` (or your frontend's exact origin)  | `*` is fine for a demo (bearer-token auth, no cookies) |
| `JWT_EXPIRY_MINUTES` | `720` (optional)                | token lifetime |

`POSTGRES_URL` is added automatically by step 3 — you don't set it manually.
(If you prefer, you may instead set `DATABASE_URL` to a full `postgres://…` string; it takes priority.)

### 5. Deploy
Click **Deploy**. When it finishes you'll get a URL like `https://<your-project>.vercel.app`.

### 6. Verify
- `https://<your-project>.vercel.app/health` → `{"status":"ok", ...}`
- `https://<your-project>.vercel.app/docs` → Swagger UI
- `https://<your-project>.vercel.app/verify` → the data dashboard (log in with the seeded demo accounts)

The **first** request may be slow (cold start + table creation + seeding). Subsequent requests are fast.

## After deploy
Send me the live URL and I'll update `FRONTEND_HANDOFF.md`, `README.md`, and the Postman
`base_url` to point at it (they currently use the local address).

## Seeded demo accounts (same as local)
- Fresher: `fresher@skillflow.local` / `Demo@123`
- PM: `pm@skillflow.local` / `Demo@123`

## Notes & limits
- **No WebSockets** — the app doesn't use them (fine for Vercel, which doesn't support them on serverless).
- **`POST /api/demo/reset`** works in production too, but it **wipes all roadmaps/reports** back to the
  empty seed — don't call it once real data is in.
- **Local development is unchanged** — `./scripts/serve_background.sh` still runs the app on SQLite
  at `http://127.0.0.1:8000`. Vercel and local are independent.
- The `10.0.128.20` LAN server and Vercel can both run; they use separate databases.
