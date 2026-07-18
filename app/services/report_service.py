import json
from datetime import datetime, date, time, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException
from ..models.domain import Roadmap, EvaluationReport, FresherProfile
from ..config import settings

def to_dt(d):
    if d is None:
        return None
    if isinstance(d, datetime):
        return d
    if isinstance(d, date):
        return datetime.combine(d, time.min)
    return None

def validate_payload(payload: dict):
    if payload is None:
        return
    serialized = json.dumps(payload, default=str)
    if len(serialized) > settings.max_report_payload_chars:
        raise HTTPException(status_code=400, detail="Report payload too large")
    # Validate KPI scores (0-100) and confidence (0-1) wherever they appear:
    # at the top level and nested under `evaluation` (both shapes are used by the frontend).
    if not isinstance(payload, dict):
        return
    kpi_lists = [payload.get("kpis")]
    evaluation = payload.get("evaluation")
    if isinstance(evaluation, dict):
        kpi_lists.append(evaluation.get("kpis"))
    for kpis in kpi_lists:
        if not isinstance(kpis, list):
            continue
        for kpi in kpis:
            if not isinstance(kpi, dict):
                continue
            score = kpi.get("score")
            if score is not None and (not isinstance(score, (int, float)) or score < 0 or score > 100):
                raise HTTPException(status_code=400, detail=f"KPI score out of range (0-100): {kpi.get('key')}")
            conf = kpi.get("confidence")
            if conf is not None and (not isinstance(conf, (int, float)) or conf < 0 or conf > 1):
                raise HTTPException(status_code=400, detail=f"KPI confidence out of range (0-1): {kpi.get('key')}")

def next_roadmap_version(db: Session, fresher_id: str) -> int:
    existing = db.query(Roadmap).filter(Roadmap.fresher_id == fresher_id).all()
    return (max([r.version for r in existing], default=0)) + 1

def find_roadmap_by_client_id(db: Session, fresher_id: str, client_roadmap_id: str):
    """Idempotency helper (change #7): a repeated client_roadmap_id must not create a duplicate."""
    if not client_roadmap_id:
        return None
    return db.query(Roadmap).filter(
        Roadmap.fresher_id == fresher_id,
        Roadmap.client_roadmap_id == client_roadmap_id,
    ).first()

def get_current_task(roadmap):
    """Return roadmap_payload.current_task (the backend-owned, authoritative task) or None."""
    if not roadmap or not isinstance(roadmap.payload, dict):
        return None
    ct = roadmap.payload.get("current_task")
    return ct if isinstance(ct, dict) else None

def get_task_by_id(roadmap, task_id):
    """Find a task by id: checks current_task first, then an optional roadmap_payload.tasks list."""
    if not roadmap or not isinstance(roadmap.payload, dict) or not task_id:
        return None
    ct = roadmap.payload.get("current_task")
    if isinstance(ct, dict) and ct.get("task_id") == task_id:
        return ct
    for t in (roadmap.payload.get("tasks") or []):
        if isinstance(t, dict) and t.get("task_id") == task_id:
            return t
    return None

def get_current_roadmap(db: Session, fresher_id: str):
    profile = db.query(FresherProfile).filter(FresherProfile.user_id == fresher_id).first()
    if profile and profile.current_roadmap_id:
        rm = db.query(Roadmap).filter(Roadmap.id == profile.current_roadmap_id).first()
        if rm:
            return rm
    return (
        db.query(Roadmap)
        .filter(Roadmap.fresher_id == fresher_id, Roadmap.status != "ARCHIVED")
        .order_by(Roadmap.version.desc())
        .first()
    )

def roadmap_out_dict(rm: Roadmap) -> dict:
    return {
        "id": rm.id,
        "client_roadmap_id": rm.client_roadmap_id,
        "fresher_id": rm.fresher_id,
        "version": rm.version,
        "title": rm.title,
        "target_role": rm.target_role,
        "start_date": rm.start_date.date() if rm.start_date else None,
        "target_completion_date": rm.target_completion_date.date() if rm.target_completion_date else None,
        "status": rm.status,
        "completion_pct": rm.completion_pct or 0.0,
        "roadmap_payload": rm.payload,
        "generated_at": rm.generated_at,
        "created_at": rm.created_at,
        "updated_at": rm.updated_at,
    }

def report_out_dict(r: EvaluationReport) -> dict:
    return {
        "id": r.id,
        "client_report_id": r.client_report_id,
        "fresher_id": r.fresher_id,
        "roadmap_id": r.roadmap_id,
        "report_type": r.report_type,
        "schema_version": r.schema_version,
        "report_date": r.report_date.date() if r.report_date else None,
        "period_start": r.period_start.date() if r.period_start else None,
        "period_end": r.period_end.date() if r.period_end else None,
        "overall_score": r.overall_score,
        "needs_human_interaction": r.needs_human_interaction,
        "report_payload": r.payload,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }

def create_report(db: Session, fresher_id: str, report_type: str, body, require_roadmap: bool = False):
    # Idempotency: same client_report_id returns existing
    existing = db.query(EvaluationReport).filter(
        EvaluationReport.client_report_id == body.client_report_id
    ).first()
    if existing:
        return existing, False

    roadmap = None
    if body.roadmap_id:
        roadmap = db.query(Roadmap).filter(
            Roadmap.id == body.roadmap_id, Roadmap.fresher_id == fresher_id
        ).first()
        if not roadmap:
            raise HTTPException(status_code=404, detail=f"Roadmap {body.roadmap_id} not found")

    # Start from the submitted payload; DAILY reports get criteria stamped from the roadmap below.
    stored_payload = dict(body.report_payload) if isinstance(body.report_payload, dict) else {}

    if report_type == "DAILY":
        # Required top-level fields for daily reports (change #6).
        if not body.roadmap_id:
            raise HTTPException(status_code=400, detail="Daily reports require roadmap_id")
        if not body.report_date:
            raise HTTPException(status_code=400, detail="Daily reports require report_date")
        if body.overall_score is None:
            raise HTTPException(status_code=400, detail="Daily reports require overall_score")
        # Required payload fields (change #6 optional-MVP validation).
        task_id = stored_payload.get("task_id")
        if not task_id:
            raise HTTPException(status_code=400, detail="Daily report_payload requires task_id")
        if not stored_payload.get("submission"):
            raise HTTPException(status_code=400, detail="Daily report_payload requires submission")
        if not stored_payload.get("evaluation"):
            raise HTTPException(status_code=400, detail="Daily report_payload requires evaluation")

        # Source-of-truth criteria (change #4): load the saved task and stamp its criteria into the
        # stored evaluation, discarding any criteria the submission tried to supply.
        task = get_task_by_id(roadmap, task_id)
        if not task:
            raise HTTPException(
                status_code=400,
                detail=f"task_id '{task_id}' does not match any task in roadmap {body.roadmap_id}",
            )
        evaluation = dict(stored_payload.get("evaluation") or {})
        evaluation["acceptance_criteria"] = task.get("acceptance_criteria", [])
        evaluation["evaluation_criteria"] = task.get("evaluation_criteria", [])
        evaluation["criteria_source"] = "backend_roadmap"
        stored_payload["evaluation"] = evaluation
        stored_payload["current_task_snapshot"] = task

    if report_type == "WEEKLY":
        if not body.period_start or not body.period_end:
            raise HTTPException(status_code=400, detail="Weekly reports require period_start and period_end")

    if report_type == "FINAL":
        if not roadmap:
            raise HTTPException(status_code=400, detail="Final reports require a valid roadmap_id")
        completed = (roadmap.status == "COMPLETED") or ((roadmap.completion_pct or 0) >= 100)
        if not completed:
            raise HTTPException(status_code=400, detail="Final report requires the roadmap to be completed (100%)")

    validate_payload(stored_payload)

    schema_version = str(stored_payload.get("schema_version", "1.0"))

    report = EvaluationReport(
        client_report_id=body.client_report_id,
        fresher_id=fresher_id,
        roadmap_id=body.roadmap_id,
        report_type=report_type,
        schema_version=schema_version,
        report_date=to_dt(body.report_date),
        period_start=to_dt(body.period_start),
        period_end=to_dt(body.period_end),
        overall_score=body.overall_score,
        needs_human_interaction=body.needs_human_interaction,
        payload=stored_payload,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report, True

def query_reports(db: Session, fresher_id: str, report_type=None, roadmap_id=None,
                  start_date=None, end_date=None, limit=50, offset=0):
    q = db.query(EvaluationReport).filter(EvaluationReport.fresher_id == fresher_id)
    if report_type:
        q = q.filter(EvaluationReport.report_type == report_type)
    if roadmap_id:
        q = q.filter(EvaluationReport.roadmap_id == roadmap_id)
    if start_date:
        q = q.filter(EvaluationReport.report_date >= to_dt(start_date))
    if end_date:
        q = q.filter(EvaluationReport.report_date <= to_dt(end_date))
    q = q.order_by(EvaluationReport.created_at.desc())
    return q.offset(offset).limit(limit).all()
