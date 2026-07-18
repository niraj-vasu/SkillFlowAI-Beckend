import pytest


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_verify_page(client):
    r = client.get("/verify")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "SkillFlow" in r.text


def test_demo_reset(client):
    r = client.post("/api/demo/reset")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_demo_reset_idempotent(client):
    client.post("/api/demo/reset")
    client.post("/api/demo/reset")
    # login still works, no duplicate accounts break login
    r = client.post("/api/auth/login", json={"email": "fresher@skillflow.local", "password": "Demo@123"})
    assert r.status_code == 200


def test_fresher_login(client):
    r = client.post("/api/auth/login", json={"email": "fresher@skillflow.local", "password": "Demo@123"})
    assert r.status_code == 200
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "FRESHER"


def test_pm_login(client):
    r = client.post("/api/auth/login", json={"email": "pm@skillflow.local", "password": "Demo@123"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "PM"


def test_invalid_login(client):
    r = client.post("/api/auth/login", json={"email": "fresher@skillflow.local", "password": "wrong"})
    assert r.status_code == 401


def test_me(client, fresher_headers):
    r = client.get("/api/auth/me", headers=fresher_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "fresher@skillflow.local"


def test_me_requires_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_fresher_cannot_access_pm_routes(client, fresher_headers):
    r = client.get("/api/pm/dashboard", headers=fresher_headers)
    assert r.status_code == 403


def test_pm_cannot_access_fresher_routes(client, pm_headers):
    r = client.get("/api/freshers/me/profile", headers=pm_headers)
    assert r.status_code == 403


def test_get_profile(client, fresher_headers):
    # Seed creates a real but EMPTY profile — no fabricated demo content.
    r = client.get("/api/freshers/me/profile", headers=fresher_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == "USR-F001"
    assert body["target_role"] is None
    assert body["resume_summary"] is None
    assert body["current_roadmap_id"] is None


def test_update_profile(client, fresher_headers):
    r = client.patch("/api/freshers/me/profile", headers=fresher_headers, json={
        "target_role": "Senior AI Product Developer",
        "resume_summary": {"summary": "updated"},
    })
    assert r.status_code == 200
    assert r.json()["target_role"] == "Senior AI Product Developer"


TASK_CRITERIA = {
    "task_id": "TASK-001",
    "task_title": "Implement API retry handler",
    "employee_facing_instruction": "Build a retry decorator.",
    "acceptance_criteria": ["Retries only on 5xx", "Raises on 4xx"],
    "evaluation_criteria": ["Correctness", "Test coverage"],
    "required_resources": ["docs"],
    "sample_input": {"url": "https://x"},
}


def _create_roadmap(client, headers, client_id="WEB-RM-001"):
    return client.post("/api/freshers/me/roadmaps", headers=headers, json={
        "client_roadmap_id": client_id,
        "title": "AI Product Developer Fresher Roadmap",
        "target_role": "AI Product Developer",
        "start_date": "2026-07-20",
        "target_completion_date": "2026-10-20",
        "roadmap_payload": {
            "weeks": [{"week": 1, "theme": "Diagnostic"}],
            "current_task": TASK_CRITERIA,
        },
    })


def test_create_roadmap(client, fresher_headers):
    r = _create_roadmap(client, fresher_headers)
    assert r.status_code == 201
    assert r.json()["status"] == "ACTIVE"


def test_roadmap_versioning(client, fresher_headers):
    r1 = _create_roadmap(client, fresher_headers, "WEB-RM-A")
    v1 = r1.json()["version"]
    r2 = _create_roadmap(client, fresher_headers, "WEB-RM-B")
    v2 = r2.json()["version"]
    assert v2 == v1 + 1
    # only one active
    rlist = client.get("/api/freshers/me/roadmaps", headers=fresher_headers).json()
    actives = [x for x in rlist if x["status"] == "ACTIVE"]
    assert len(actives) == 1


def test_current_roadmap(client, fresher_headers):
    _create_roadmap(client, fresher_headers, "WEB-RM-CUR")
    r = client.get("/api/freshers/me/roadmaps/current", headers=fresher_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "ACTIVE"


def test_roadmap_progress(client, fresher_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-P").json()
    r = client.patch(f"/api/freshers/me/roadmaps/{rm['id']}/progress", headers=fresher_headers,
                     json={"completion_pct": 40})
    assert r.status_code == 200
    assert r.json()["completion_pct"] == 40
    # payload not wiped
    assert r.json()["roadmap_payload"]["weeks"]


def test_roadmap_complete(client, fresher_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-C").json()
    r = client.post(f"/api/freshers/me/roadmaps/{rm['id']}/complete", headers=fresher_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "COMPLETED"
    assert r.json()["completion_pct"] == 100


def test_roadmap_idempotent_client_id(client, fresher_headers):
    r1 = _create_roadmap(client, fresher_headers, "WEB-RM-IDEM")
    r2 = _create_roadmap(client, fresher_headers, "WEB-RM-IDEM")
    assert r1.json()["id"] == r2.json()["id"]
    assert r1.json()["version"] == r2.json()["version"]
    # second call is idempotent, not a new version
    assert r2.status_code == 200
    rlist = client.get("/api/freshers/me/roadmaps", headers=fresher_headers).json()
    assert len([x for x in rlist if x["client_roadmap_id"] == "WEB-RM-IDEM"]) == 1


def test_roadmap_requires_target_role(client, fresher_headers):
    r = client.post("/api/freshers/me/roadmaps", headers=fresher_headers, json={
        "client_roadmap_id": "WEB-RM-NOROLE",
        "title": "Missing role",
        "roadmap_payload": {"weeks": []},
    })
    assert r.status_code == 422


def test_roadmap_requires_nonempty_payload(client, fresher_headers):
    r = client.post("/api/freshers/me/roadmaps", headers=fresher_headers, json={
        "client_roadmap_id": "WEB-RM-EMPTY",
        "title": "Empty payload",
        "target_role": "AI Product Developer",
        "roadmap_payload": {},
    })
    assert r.status_code == 422


def test_profile_nested_metadata_roundtrips(client, fresher_headers):
    nested = {
        "resume_parsing_status": {"state": "done", "confidence": 0.9},
        "resume_analysis": {"skills": [{"name": "Python", "verified": False}]},
        "manual_fallback_data": {"entered_by": "supervisor"},
        "supervisor_confirmation": {"confirmed": True, "by": "PM-001"},
    }
    r = client.patch("/api/freshers/me/profile", headers=fresher_headers,
                     json={"profile_metadata": nested})
    assert r.status_code == 200
    got = client.get("/api/freshers/me/profile", headers=fresher_headers).json()
    assert got["profile_metadata"]["resume_analysis"]["skills"][0]["name"] == "Python"
    assert got["profile_metadata"]["supervisor_confirmation"]["confirmed"] is True


def _daily(client, headers, roadmap_id, client_id="WEB-DAILY-1", task_id="TASK-001", extra_payload=None):
    payload = {
        "schema_version": "1.0",
        "task_id": task_id,
        "submission": {"summary": "Implemented retry decorator", "pull_request": "PR-12"},
        "ai_usage_disclosure": {"used_ai": True, "tools": ["Copilot"]},
        "evaluation": {
            "verified_skills": ["API integration", "Responsible AI usage"],
            "weak_areas": ["Timeout testing", "Failure-state communication"],
            "evidence": ["8 tests passed", "1 timeout test failed"],
            "dashboard_update": {"next_focus": "Timeout handling", "improvement_pct": 12.5},
            "kpis": [{"key": "problem_solving", "name": "Problem Solving", "score": 78, "confidence": 0.88}],
        },
        "qna": {"questions": [{"question": "Prevent infinite retries?", "answer": "Max retry + backoff", "score": 82}]},
    }
    if extra_payload:
        payload.update(extra_payload)
    return client.post("/api/freshers/me/reports/daily", headers=headers, json={
        "client_report_id": client_id,
        "roadmap_id": roadmap_id,
        "report_date": "2026-07-18",
        "overall_score": 76,
        "needs_human_interaction": True,
        "report_payload": payload,
    })


def test_daily_report_create(client, fresher_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-D").json()
    r = _daily(client, fresher_headers, rm["id"])
    assert r.status_code == 200
    assert r.json()["report_type"] == "DAILY"


def test_daily_report_idempotent(client, fresher_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-DI").json()
    r1 = _daily(client, fresher_headers, rm["id"], "WEB-DAILY-IDEM")
    r2 = _daily(client, fresher_headers, rm["id"], "WEB-DAILY-IDEM")
    assert r1.json()["id"] == r2.json()["id"]
    # only one record
    lst = client.get("/api/freshers/me/reports/daily", headers=fresher_headers).json()
    matching = [x for x in lst if x["client_report_id"] == "WEB-DAILY-IDEM"]
    assert len(matching) == 1


def test_daily_report_validation_score(client, fresher_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-V").json()
    r = client.post("/api/freshers/me/reports/daily", headers=fresher_headers, json={
        "client_report_id": "WEB-DAILY-BAD",
        "roadmap_id": rm["id"],
        "overall_score": 150,
        "report_payload": {},
    })
    assert r.status_code == 422


def test_daily_report_kpi_validation(client, fresher_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-VK").json()
    # Full valid envelope, but a top-level KPI score is out of range -> 400
    r = _daily(client, fresher_headers, rm["id"], "WEB-DAILY-BADKPI",
               extra_payload={"kpis": [{"key": "x", "score": 500}]})
    assert r.status_code == 400


def test_daily_requires_task_id(client, fresher_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-NOTASK").json()
    r = client.post("/api/freshers/me/reports/daily", headers=fresher_headers, json={
        "client_report_id": "WEB-DAILY-NOTASK",
        "roadmap_id": rm["id"],
        "report_date": "2026-07-18",
        "overall_score": 70,
        "report_payload": {"submission": {"x": 1}, "evaluation": {"verified_skills": []}},
    })
    assert r.status_code == 400


def test_daily_unknown_task_id_rejected(client, fresher_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-BADTASK").json()
    r = _daily(client, fresher_headers, rm["id"], "WEB-DAILY-BADTASK", task_id="TASK-999")
    assert r.status_code == 400


def test_daily_criteria_come_from_backend(client, fresher_headers):
    """Change #4: criteria in the stored report must come from the saved roadmap task,
    never from what the frontend submitted."""
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-CRIT").json()
    # Frontend tries to sneak in easier criteria
    r = _daily(client, fresher_headers, rm["id"], "WEB-DAILY-CRIT",
               extra_payload={"evaluation": {
                   "verified_skills": ["API integration"],
                   "weak_areas": ["Timeouts"],
                   "acceptance_criteria": ["ANYTHING GOES"],
                   "evaluation_criteria": ["TRUST ME"],
               }})
    assert r.status_code == 200
    ev = r.json()["report_payload"]["evaluation"]
    # Backend overwrote with the saved roadmap criteria
    assert ev["acceptance_criteria"] == TASK_CRITERIA["acceptance_criteria"]
    assert ev["evaluation_criteria"] == TASK_CRITERIA["evaluation_criteria"]
    assert ev["criteria_source"] == "backend_roadmap"
    assert r.json()["report_payload"]["current_task_snapshot"]["task_id"] == "TASK-001"


def test_weekly_report(client, fresher_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-W").json()
    r = client.post("/api/freshers/me/reports/weekly", headers=fresher_headers, json={
        "client_report_id": "WEB-WEEKLY-1",
        "roadmap_id": rm["id"],
        "period_start": "2026-07-13",
        "period_end": "2026-07-18",
        "overall_score": 74,
        "report_payload": {"strengths": ["consistent"]},
    })
    assert r.status_code == 200
    assert r.json()["report_type"] == "WEEKLY"


def test_weekly_requires_period(client, fresher_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-WP").json()
    r = client.post("/api/freshers/me/reports/weekly", headers=fresher_headers, json={
        "client_report_id": "WEB-WEEKLY-NOPERIOD",
        "roadmap_id": rm["id"],
        "report_payload": {},
    })
    assert r.status_code == 400


def test_final_report_rejected_before_completion(client, fresher_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-F1").json()
    r = client.post("/api/freshers/me/reports/final", headers=fresher_headers, json={
        "client_report_id": "WEB-FINAL-EARLY",
        "roadmap_id": rm["id"],
        "report_payload": {},
    })
    assert r.status_code == 400


def test_final_report_after_completion(client, fresher_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-F2").json()
    client.post(f"/api/freshers/me/roadmaps/{rm['id']}/complete", headers=fresher_headers)
    r = client.post("/api/freshers/me/reports/final", headers=fresher_headers, json={
        "client_report_id": "WEB-FINAL-OK",
        "roadmap_id": rm["id"],
        "report_payload": {"summary": "great"},
    })
    assert r.status_code == 200
    assert r.json()["report_type"] == "FINAL"


def test_pm_list_freshers(client, pm_headers):
    r = client.get("/api/pm/freshers", headers=pm_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == "USR-F001"


def test_pm_access_assigned_fresher(client, pm_headers):
    r = client.get("/api/pm/freshers/USR-F001/overview", headers=pm_headers)
    assert r.status_code == 200
    assert r.json()["fresher"]["id"] == "USR-F001"


def test_pm_blocked_from_unassigned(client, pm_headers, db):
    # create another fresher not assigned to this PM
    from app.models.domain import User
    from app.services.auth_service import hash_password
    other = User(id="USR-F999", name="Other", email="other@skillflow.local",
                 password_hash=hash_password("Demo@123"), role="FRESHER", is_active=True)
    db.add(other)
    db.commit()
    r = client.get("/api/pm/freshers/USR-F999/overview", headers=pm_headers)
    assert r.status_code == 403


def test_pm_missing_fresher_404(client, pm_headers):
    r = client.get("/api/pm/freshers/NOPE/overview", headers=pm_headers)
    assert r.status_code == 404


def test_pm_dashboard(client, pm_headers):
    r = client.get("/api/pm/dashboard", headers=pm_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["assigned_freshers"] == 1
    assert len(data["freshers"]) == 1


def test_pm_dashboard_reflects_new_report(client, fresher_headers, pm_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-DASH").json()
    _daily(client, fresher_headers, rm["id"], "WEB-DAILY-DASH")
    r = client.get("/api/pm/dashboard", headers=pm_headers)
    card = r.json()["freshers"][0]
    assert card["latest_daily_report"] is not None
    assert card["latest_daily_report"]["client_report_id"] == "WEB-DAILY-DASH"


def test_pm_dashboard_view_fields(client, fresher_headers, pm_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-VIEW").json()
    _daily(client, fresher_headers, rm["id"], "WEB-DAILY-VIEW")
    card = client.get("/api/pm/dashboard", headers=pm_headers).json()["freshers"][0]
    assert card["strongest_skill"] == "API integration"        # first verified skill
    assert card["current_gap"] == "Timeout testing"            # first weak area
    assert card["next_learning_focus"] == "Timeout handling"   # from dashboard_update
    assert card["mentor_required"] is True
    assert card["current_assigned_task"]["task_id"] == "TASK-001"
    assert card["evidence"]


def test_pm_overview_has_insights(client, fresher_headers, pm_headers):
    rm = _create_roadmap(client, fresher_headers, "WEB-RM-OV").json()
    _daily(client, fresher_headers, rm["id"], "WEB-DAILY-OV")
    ov = client.get("/api/pm/freshers/USR-F001/overview", headers=pm_headers).json()
    assert ov["insights"]["strongest_skill"] == "API integration"
    assert ov["insights"]["current_assigned_task"]["task_id"] == "TASK-001"


def test_e2e_full_flow(client):
    # reset
    assert client.post("/api/demo/reset").status_code == 200
    # fresher login
    ft = client.post("/api/auth/login", json={"email": "fresher@skillflow.local", "password": "Demo@123"}).json()["access_token"]
    fh = {"Authorization": f"Bearer {ft}"}
    # profile update
    assert client.patch("/api/freshers/me/profile", headers=fh, json={"target_role": "AI Product Developer"}).status_code == 200
    # roadmap (includes the backend-owned current_task with criteria)
    rm = client.post("/api/freshers/me/roadmaps", headers=fh, json={
        "client_roadmap_id": "E2E-RM", "title": "E2E Roadmap",
        "target_role": "AI Product Developer", "start_date": "2026-07-20",
        "target_completion_date": "2026-10-20",
        "roadmap_payload": {"weeks": [], "current_task": TASK_CRITERIA},
    }).json()
    # current roadmap
    assert client.get("/api/freshers/me/roadmaps/current", headers=fh).status_code == 200
    # daily report with submission, evaluation (incl. Q&A)
    d = _daily(client, fh, rm["id"], "E2E-DAILY")
    assert d.status_code == 200
    # backend stamped the authoritative criteria
    assert d.json()["report_payload"]["evaluation"]["criteria_source"] == "backend_roadmap"
    # PM login
    pt = client.post("/api/auth/login", json={"email": "pm@skillflow.local", "password": "Demo@123"}).json()["access_token"]
    ph = {"Authorization": f"Bearer {pt}"}
    # PM dashboard sees daily
    dash = client.get("/api/pm/dashboard", headers=ph).json()
    assert dash["freshers"][0]["latest_daily_report"]["client_report_id"] == "E2E-DAILY"
    # weekly
    w = client.post("/api/freshers/me/reports/weekly", headers=fh, json={
        "client_report_id": "E2E-WEEKLY", "roadmap_id": rm["id"],
        "period_start": "2026-07-13", "period_end": "2026-07-18",
        "overall_score": 74, "report_payload": {},
    })
    assert w.status_code == 200
    # PM retrieves weekly
    pm_weekly = client.get("/api/pm/freshers/USR-F001/reports/weekly", headers=ph).json()
    assert any(x["client_report_id"] == "E2E-WEEKLY" for x in pm_weekly)
    # complete roadmap
    assert client.post(f"/api/freshers/me/roadmaps/{rm['id']}/complete", headers=fh).status_code == 200
    # final report
    f = client.post("/api/freshers/me/reports/final", headers=fh, json={
        "client_report_id": "E2E-FINAL", "roadmap_id": rm["id"], "report_payload": {"summary": "done"},
    })
    assert f.status_code == 200
    # PM dashboard sees final
    dash2 = client.get("/api/pm/dashboard", headers=ph).json()
    assert dash2["freshers"][0]["final_report"]["client_report_id"] == "E2E-FINAL"


def test_works_without_ai_key(client, fresher_headers):
    # No AI key configured; all core flows must work
    r = client.get("/api/freshers/me/profile", headers=fresher_headers)
    assert r.status_code == 200
