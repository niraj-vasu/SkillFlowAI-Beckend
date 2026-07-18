# SkillFlow AI v2 — Frontend Handoff

This backend stores and serves data only. It performs **no AI generation** — the frontend dashboards own all AI agents (roadmap generation, work evaluation, Q&A, and daily/weekly/final report generation) and submit their results to this API for storage, access control, and retrieval.

## Base URL & docs

```
Base URL:  http://10.0.128.20:8000
API docs:  http://10.0.128.20:8000/docs
```

All REST endpoints are under `/api/`.

## Postman collection

A ready-to-run collection ships alongside this doc: **`SkillFlow_AI.postman_collection.json`**.

1. In Postman: **Import** → select the file. It creates a "SkillFlow AI v2 — Backend" collection with folders **System / Auth / Fresher / PM** (31 requests).
2. It defines a `base_url` collection variable (`http://10.0.128.20:8000`) — edit it if your server runs elsewhere.
3. Run **Auth → Login (Fresher)** and **Auth → Login (PM)** first. Their test scripts automatically capture `{{fresher_token}}` and `{{pm_token}}`; every other request already sends the correct bearer token.
4. **Create Roadmap** stores `{{roadmap_id}}` and **Create Daily Report** stores `{{report_id}}`, so the later requests resolve without manual copying.
5. The whole collection also runs top-to-bottom in the **Collection Runner** (verified end-to-end with Newman: 31/31 requests pass). Note the final report requires the roadmap to be completed first — the Runner order (Roadmaps → Reports) already handles this via the **Complete Roadmap** request.

Every request includes a description and a realistic example body, so the collection doubles as live, executable API documentation.

## CORS

- `CORS_ORIGINS=*` by default (configurable in `.env`).
- Because the origin is a wildcard, `allow_credentials` is **disabled** — cookies are not used for auth, so this has no effect on you.
- Auth is carried entirely in the `Authorization: Bearer <token>` header, not cookies, so wildcard CORS works fine for local dev.
- If you later need `allow_credentials=true` (e.g. cookie-based auth), you must set explicit origins instead of `*`. Common dev origins to list in `CORS_ORIGINS` (comma-separated) if needed: `http://localhost:3000`, `http://localhost:5173`, `http://localhost:8080`.

## Login flow & bearer tokens

1. `POST /api/auth/login` with `{ "email": ..., "password": ... }`.
2. Store the returned `access_token`.
3. Send it on every subsequent request as `Authorization: Bearer <access_token>`.
4. `GET /api/auth/me` returns the current user derived from the token — useful for rehydrating session state on page load.

There is no refresh-token endpoint in v2; tokens are valid for `JWT_EXPIRY_MINUTES` (default 720 minutes / 12 hours). When a token expires, requests return `401` — re-run the login flow.

## Seeded credentials

Both accounts use password `Demo@123`.

| Role    | Email                       | User ID     | Name         |
|---------|------------------------------|-------------|--------------|
| Fresher | `fresher@skillflow.local`    | `USR-F001`  | Aarav Patel  |
| PM      | `pm@skillflow.local`         | `USR-PM001` | Priya Menon  |

The seeded fresher is assigned to the seeded PM. Call `POST /api/demo/reset` any time to restore clean demo state (idempotent — safe to call repeatedly).

## Endpoint summary

### System

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/api/demo/reset` | Reset to seeded demo state (idempotent) |

### Auth

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login` | Log in, get bearer token + user object |
| GET | `/api/auth/me` | Get the current authenticated user |

### Fresher (bearer token, role FRESHER — identity always comes from the token, never a client-supplied id)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/freshers/me/profile` | Get own profile |
| PATCH | `/api/freshers/me/profile` | Update own profile (target_role, joining_date, resume_summary, interview_evaluation, profile_metadata only) |
| POST | `/api/freshers/me/roadmaps` | Create a new roadmap version (archives prior ACTIVE one) |
| GET | `/api/freshers/me/roadmaps` | List all own roadmap versions |
| GET | `/api/freshers/me/roadmaps/current` | Get current ACTIVE roadmap |
| GET | `/api/freshers/me/roadmaps/{roadmap_id}` | Get a specific roadmap by id |
| PATCH | `/api/freshers/me/roadmaps/{roadmap_id}/progress` | Update completion_pct and/or status (partial update, never replaces payload) |
| POST | `/api/freshers/me/roadmaps/{roadmap_id}/complete` | Mark roadmap COMPLETED, completion_pct → 100 (does not create a final report) |
| POST | `/api/freshers/me/reports/daily` | Submit a daily report |
| POST | `/api/freshers/me/reports/weekly` | Submit a weekly report (requires period_start & period_end) |
| POST | `/api/freshers/me/reports/final` | Submit a final report (roadmap must be COMPLETED or 100%) |
| GET | `/api/freshers/me/reports` | List own reports (filters: roadmap_id, start_date, end_date, limit, offset) |
| GET | `/api/freshers/me/reports/daily` | List own daily reports |
| GET | `/api/freshers/me/reports/weekly` | List own weekly reports |
| GET | `/api/freshers/me/reports/final` | List own final reports |
| GET | `/api/freshers/me/reports/{report_id}` | Get a specific report by id |

### PM (bearer token, role PM — assignment enforced on every endpoint)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/pm/freshers` | List freshers assigned to this PM |
| GET | `/api/pm/freshers/{fresher_id}/overview` | Overview of one assigned fresher |
| GET | `/api/pm/freshers/{fresher_id}/roadmaps` | All roadmap versions for one assigned fresher |
| GET | `/api/pm/freshers/{fresher_id}/roadmaps/current` | Current roadmap for one assigned fresher |
| GET | `/api/pm/freshers/{fresher_id}/reports` | All reports for one assigned fresher |
| GET | `/api/pm/freshers/{fresher_id}/reports/daily` | Daily reports for one assigned fresher |
| GET | `/api/pm/freshers/{fresher_id}/reports/weekly` | Weekly reports for one assigned fresher |
| GET | `/api/pm/freshers/{fresher_id}/reports/final` | Final report(s) for one assigned fresher |
| GET | `/api/pm/dashboard` | Full dashboard: all assigned freshers, roadmap progress, latest reports, flags |

## Example requests & responses

### Login

```bash
curl -X POST http://10.0.128.20:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "fresher@skillflow.local", "password": "Demo@123"}'
```

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": "USR-F001",
    "email": "fresher@skillflow.local",
    "name": "Aarav Patel",
    "role": "FRESHER",
    "is_active": true
  }
}
```

### Create a roadmap

```
POST /api/freshers/me/roadmaps
Authorization: Bearer <fresher_token>
Content-Type: application/json
```

> **The example values below are placeholders.** The backend is domain-agnostic — it stores whatever your AI agent generates for any department, role, or discipline (design, marketing, data, sales, engineering, …). Nothing here is hardcoded to a particular field, language, or tool. Fill every `<…>` with your real, dynamically-generated content.

```json
{
  "client_roadmap_id": "<your client-generated roadmap id>",
  "title": "<roadmap title>",
  "target_role": "<the fresher's target role / department>",
  "start_date": "2026-07-20",
  "target_completion_date": "2026-10-20",
  "roadmap_payload": {
    "schema_version": "1.0",
    "generation_mode": "diagnostic",
    "pace_status": "no_evidence",
    "weeks": [],
    "competencies": ["<competency_key>", "<competency_key>"],
    "milestones": [],
    "completion_criteria": "<how completion is defined>",
    "current_task": {
      "task_id": "<task id, e.g. TASK-001>",
      "task_title": "<title of the task the agent generated>",
      "employee_facing_instruction": "<instructions shown to the employee>",
      "sample_input": { "<any": "domain-specific example input>" },
      "required_resources": ["<resource url or reference>"],
      "acceptance_criteria": ["<criterion 1>", "<criterion 2>"],
      "evaluation_criteria": ["<criterion 1>", "<criterion 2>"]
    }
  }
}
```

- **Required top-level fields:** `client_roadmap_id`, `title`, `target_role`, `roadmap_payload` (must be non-empty). Missing/blank → `422`.
- **Idempotency:** re-POSTing the **same `client_roadmap_id`** returns the existing roadmap (`200`) instead of creating a new version. A **new version** requires a **new `client_roadmap_id`** (previous ACTIVE roadmap is auto-archived).
- **`current_task`** is the backend-owned task the daily report is graded against — see [Backend-owned criteria](#backend-owned-criteria-source-of-truth). Its shape is flexible; only `task_id` is required by the backend (so daily reports can reference it). Everything else — instruction, resources, criteria — is defined entirely by your agent for the relevant department/role.
- Response (`201`, or `200` if idempotent) includes `roadmap_payload` plus `id`, `version`, `status` (`ACTIVE`), `completion_pct`.

### Submit a daily report

> Again, the content below (skills, evidence, task) is illustrative only — the backend stores your agent's real output for any domain. The structural keys (`task_id`, `submission`, `evaluation`, `verified_skills`, `weak_areas`, `dashboard_update`) are what matter.

```
POST /api/freshers/me/reports/daily
Authorization: Bearer <fresher_token>
Content-Type: application/json
```

```json
{
  "client_report_id": "WEB-DAILY-2026-07-18-USR-F001",
  "roadmap_id": "<roadmap uuid>",
  "report_date": "2026-07-18",
  "overall_score": 76,
  "needs_human_interaction": true,
  "report_payload": {
    "schema_version": "1.0",
    "task_id": "<task id from the roadmap's current_task, e.g. TASK-001>",
    "submission": {
      "summary": "<what the employee submitted>",
      "reference": "<link or id to the work>"
    },
    "ai_usage_disclosure": {
      "used_ai": true,
      "tools": ["<tool>"],
      "what_ai_generated": "<what the AI produced>",
      "what_employee_corrected": "<what the employee changed>"
    },
    "evaluation": {
      "verified_skills": ["<skill name>", "<skill name>"],
      "weak_areas": ["<gap>", "<gap>"],
      "evidence": ["<evidence item>", "<evidence item>"],
      "dashboard_update": { "next_focus": "<next focus>", "improvement_pct": 12.5 },
      "kpis": [
        { "key": "<kpi_key>", "name": "<KPI Name>", "score": 78, "confidence": 0.88 }
      ]
    },
    "qna": {
      "questions": [
        { "question": "<question the agent asked>", "answer": "<employee answer>", "score": 82 }
      ],
      "summary": "<short summary>"
    }
  }
}
```

**Required top-level fields (daily):** `client_report_id`, `roadmap_id`, `report_date`, `overall_score` (0–100), `report_payload`. **Required inside `report_payload`:** `task_id`, `submission`, `evaluation`. Missing any → `400` (out-of-range `overall_score` → `422`).

> **The backend overwrites your criteria.** On submit, the backend finds `current_task` by `task_id` in the report's roadmap and **replaces** `report_payload.evaluation.acceptance_criteria` and `.evaluation_criteria` with the saved roadmap values, adds `evaluation.criteria_source: "backend_roadmap"`, and stores a `report_payload.current_task_snapshot`. Any criteria you send are ignored. If `task_id` isn't found in the roadmap → `400`. See [Backend-owned criteria](#backend-owned-criteria-source-of-truth).

Response includes the stored `report_payload` (with the stamped criteria + `current_task_snapshot`) plus flat fields: `id`, `client_report_id`, `fresher_id`, `roadmap_id`, `report_type`, `schema_version`, `report_date`, `period_start`, `period_end`, `overall_score`, `needs_human_interaction`, `created_at`, `updated_at`.

**KPI values** anywhere (top-level `kpis` or `evaluation.kpis`) must have `score` 0–100 and `confidence` 0–1, or the request fails with `400`. Payloads are capped at 200,000 chars.

**Weekly reports** (`POST /api/freshers/me/reports/weekly`) require `period_start` and `period_end`; they are not subject to the daily `task_id`/`submission`/`evaluation` rule.

**Final reports** (`POST /api/freshers/me/reports/final`) require `roadmap_id` for a roadmap already `COMPLETED` or at 100% — otherwise `400`.

### Backend-owned criteria (source of truth)

The backend runs **no AI** — your frontend agent does all evaluation. To keep evaluations honest and tamper-proof:

1. Store the task (with `acceptance_criteria` + `evaluation_criteria`) inside `roadmap_payload.current_task` when you create the roadmap. Fetch it any time via `GET /api/freshers/me/roadmaps/current` (or the PM sees it under `current_assigned_task`).
2. Your agent evaluates the submission **against those saved criteria**.
3. On `POST .../reports/daily` you send `task_id` + `submission` + `evaluation`. The backend re-stamps the saved criteria into the stored record and ignores any criteria in your submission. This means a hand-edited submission can't weaken the criteria — the persisted record always cites the roadmap's authoritative task.

### PM dashboard

```
GET /api/pm/dashboard
Authorization: Bearer <pm_token>
```

```json
{
  "pm": { "id": "USR-PM001", "email": "pm@skillflow.local", "name": "Priya Menon", "role": "PM", "is_active": true },
  "summary": { "assigned_freshers": 1, "freshers_needing_interaction": 1, "reports_received_this_week": 2 },
  "freshers": [
    {
      "fresher": { "id": "USR-F001", "email": "fresher@skillflow.local", "name": "Aarav Patel", "role": "FRESHER", "is_active": true },
      "current_roadmap": { "id": "...", "version": 1, "status": "ACTIVE", "completion_pct": 25.0, "roadmap_payload": {} },
      "roadmap_progress": 25.0,
      "latest_daily_report": { "client_report_id": "...", "overall_score": 76.0, "report_payload": {} },
      "latest_weekly_report": null,
      "final_report": null,
      "strongest_skill": "<top verified skill>",
      "current_gap": "<top weak area>",
      "next_learning_focus": "<next focus>",
      "mentor_required": true,
      "evidence": ["<evidence item>", "<evidence item>"],
      "current_assigned_task": { "task_id": "TASK-001", "task_title": "<current task title>", "acceptance_criteria": ["..."] },
      "dashboard_update": { "next_focus": "<next focus>", "improvement_pct": 12.5 },
      "strengths": ["<skill name>", "<skill name>"],
      "weaknesses": ["<gap>", "<gap>"],
      "needs_human_interaction": true,
      "last_activity_at": "2026-07-18T17:30:00Z"
    }
  ]
}
```

**Where each dashboard field comes from** (the backend computes these for you, but here's the mapping):

| Dashboard label | Card field | Source path |
|---|---|---|
| Strongest skill | `strongest_skill` | `latest_daily_report.report_payload.evaluation.verified_skills[0]` |
| Current gap | `current_gap` | `latest_daily_report.report_payload.evaluation.weak_areas[0]` |
| Next learning focus | `next_learning_focus` | `evaluation.dashboard_update.next_focus` (falls back to `recommended_next_focus`) |
| Mentor required | `mentor_required` | `latest_daily_report.needs_human_interaction` |
| Evidence | `evidence` | `evaluation.evidence` |
| Current assigned task | `current_assigned_task` | `current_roadmap.roadmap_payload.current_task` |

`verified_skills` / `weak_areas` are lists of skill-name strings (strongest = first). The same fields are available per fresher under `insights` on `GET /api/pm/freshers/{fresher_id}/overview`. `strengths`/`weaknesses` remain for backward compatibility.

Both the fresher-facing views and the PM dashboard read the same source of truth — a report submitted by a fresher appears in the PM dashboard on the very next request (verified). There are no WebSockets in v2; the PM dashboard is REST polling only.

## Recommended dashboard sequences

### Fresher dashboard flow

- `POST /api/auth/login` → store token
- `GET /api/freshers/me/profile` → show profile header
- `GET /api/freshers/me/roadmaps/current` → show active roadmap + completion_pct
- `PATCH /api/freshers/me/roadmaps/{roadmap_id}/progress` → update progress as work is done
- Frontend AI agent generates a daily evaluation → `POST /api/freshers/me/reports/daily` → show score/feedback
- At period boundaries: frontend AI agent generates a weekly summary → `POST /api/freshers/me/reports/weekly`
- When roadmap hits 100%/COMPLETED: `POST /api/freshers/me/roadmaps/{roadmap_id}/complete`, then frontend AI agent generates a final report → `POST /api/freshers/me/reports/final`
- `GET /api/freshers/me/reports` (with filters) → history view

### PM dashboard flow

- `POST /api/auth/login` → store token
- `GET /api/pm/freshers` → list of assigned freshers
- `GET /api/pm/dashboard` → team overview cards (poll on an interval, see below)
- `needs_human_interaction: true` on a card → show an alert badge
- Click into a fresher card:
  - `GET /api/pm/freshers/{fresher_id}/overview`
  - `GET /api/pm/freshers/{fresher_id}/roadmaps/current`
  - `GET /api/pm/freshers/{fresher_id}/reports` (or `/daily`, `/weekly`, `/final`)

## JavaScript fetch examples

### Login and store token

```js
async function login(email, password) {
  const res = await fetch('http://10.0.128.20:8000/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  if (!res.ok) throw new Error(`Login failed: ${res.status}`);
  const data = await res.json();
  localStorage.setItem('access_token', data.access_token);
  return data.user;
}
```

### Authenticated GET (profile)

```js
async function getProfile() {
  const token = localStorage.getItem('access_token');
  const res = await fetch('http://10.0.128.20:8000/api/freshers/me/profile', {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error(`Failed to fetch profile: ${res.status}`);
  return res.json();
}
```

### POST daily report

```js
async function submitDailyReport(reportBody) {
  const token = localStorage.getItem('access_token');
  const res = await fetch('http://10.0.128.20:8000/api/freshers/me/reports/daily', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(reportBody)
  });
  if (!res.ok) throw new Error(`Failed to submit daily report: ${res.status}`);
  return res.json();
}
```

### PM dashboard poll

```js
async function pollPmDashboard(onUpdate, intervalMs = 20000) {
  const token = localStorage.getItem('access_token');
  async function fetchOnce() {
    const res = await fetch('http://10.0.128.20:8000/api/pm/dashboard', {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!res.ok) throw new Error(`Dashboard fetch failed: ${res.status}`);
    onUpdate(await res.json());
  }
  await fetchOnce();
  return setInterval(fetchOnce, intervalMs);
}
```

## Polling recommendation

There is no WebSocket or push mechanism in v2. Poll `GET /api/pm/dashboard` every **15–30 seconds** for the PM view. A fresher's newly submitted report is visible on the very next poll — no delay to account for.

## Error handling

| Status | Meaning | When you'll see it |
|---|---|---|
| 400 | Malformed business data | Bad KPI score, weekly report missing period_start/period_end, final report submitted before roadmap is completed |
| 401 | Missing or invalid token | No `Authorization` header, or an expired/invalid token — re-login |
| 403 | Role or assignment violation | Wrong role for the endpoint, or a PM requesting a fresher not assigned to them |
| 404 | Resource not found | Missing fresher, roadmap, or report id |
| 422 | Request-schema validation error | e.g. `overall_score` > 100, wrong field type, missing required field |

**Idempotent duplicates:** submitting a report with a `client_report_id` that already exists does **not** return `409` — it returns the existing record with `200 OK`. Design your submission retry logic around this: it's always safe to retry a report submission after a network error, since duplicates will never be created.
