from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from ..database import get_db
from ..models.domain import User, FresherProfile, Roadmap, EvaluationReport, PMFresherAssignment
from ..schemas.v2_schemas import RoadmapOut, ReportOut
from ..schemas.auth_schemas import UserOut
from .deps import require_pm, get_assigned_fresher
from ..services.report_service import (
    get_current_roadmap, get_current_task, roadmap_out_dict, report_out_dict, query_reports,
)

router = APIRouter(prefix="/api/pm", tags=["pm"])

def _skill_name(item):
    """Skills are a list of names (per frontend), but tolerate {skill|name|competency} dicts too."""
    if isinstance(item, dict):
        return item.get("skill") or item.get("name") or item.get("competency")
    return item

def build_fresher_insights(daily, current) -> dict:
    """Extract the PM-dashboard view fields from the latest daily report + current roadmap (change #5).

    Reads:
      latest_daily_report.report_payload.evaluation.verified_skills / .weak_areas / .dashboard_update / .evidence
      latest_daily_report.needs_human_interaction, .overall_score
      current_roadmap.roadmap_payload.current_task
    """
    payload = (daily.payload if daily else {}) or {}
    if not isinstance(payload, dict):
        payload = {}
    evaluation = payload.get("evaluation") or {}
    if not isinstance(evaluation, dict):
        evaluation = {}

    verified = evaluation.get("verified_skills") or []
    weak = evaluation.get("weak_areas") or []
    dashboard_update = evaluation.get("dashboard_update") or payload.get("dashboard_update") or {}

    strengths = [_skill_name(s) for s in verified if _skill_name(s)] or (payload.get("strengths") or [])
    weaknesses = [_skill_name(w) for w in weak if _skill_name(w)] or (payload.get("weaknesses") or [])

    next_focus = None
    if isinstance(dashboard_update, dict):
        next_focus = dashboard_update.get("next_focus") or dashboard_update.get("next_learning_focus")
    if not next_focus:
        rnf = evaluation.get("recommended_next_focus")
        if isinstance(rnf, list) and rnf:
            next_focus = _skill_name(rnf[0])
        elif isinstance(rnf, str):
            next_focus = rnf

    evidence = evaluation.get("evidence") or payload.get("evidence") or []

    return {
        "strongest_skill": strengths[0] if strengths else None,
        "current_gap": weaknesses[0] if weaknesses else None,
        "next_learning_focus": next_focus,
        "mentor_required": bool(daily.needs_human_interaction) if daily else False,
        "evidence": evidence,
        "current_assigned_task": get_current_task(current),
        "overall_score": daily.overall_score if daily else None,
        "dashboard_update": dashboard_update,
        # back-compat fields
        "strengths": strengths,
        "weaknesses": weaknesses,
    }

def _assigned_fresher_ids(db: Session, pm_id: str) -> List[str]:
    rows = db.query(PMFresherAssignment).filter(
        PMFresherAssignment.pm_user_id == pm_id, PMFresherAssignment.active == True
    ).all()
    return [r.fresher_user_id for r in rows]

def _user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role, "is_active": u.is_active}

def _latest_report(db: Session, fresher_id: str, rtype: str):
    return (
        db.query(EvaluationReport)
        .filter(EvaluationReport.fresher_id == fresher_id, EvaluationReport.report_type == rtype)
        .order_by(EvaluationReport.created_at.desc())
        .first()
    )

@router.get("/freshers")
def list_freshers(pm: User = Depends(require_pm), db: Session = Depends(get_db)):
    ids = _assigned_fresher_ids(db, pm.id)
    users = db.query(User).filter(User.id.in_(ids)).all() if ids else []
    return [_user_out(u) for u in users]

@router.get("/freshers/{fresher_id}/overview")
def fresher_overview(fresher_id: str, pm: User = Depends(require_pm), db: Session = Depends(get_db)):
    fresher = get_assigned_fresher(pm, fresher_id, db)
    profile = db.query(FresherProfile).filter(FresherProfile.user_id == fresher_id).first()
    current = get_current_roadmap(db, fresher_id)
    daily = _latest_report(db, fresher_id, "DAILY")
    weekly = _latest_report(db, fresher_id, "WEEKLY")
    final = _latest_report(db, fresher_id, "FINAL")
    return {
        "fresher": _user_out(fresher),
        "profile": {
            "target_role": profile.target_role if profile else None,
            "joining_date": profile.joining_date.date().isoformat() if profile and profile.joining_date else None,
            "resume_summary": profile.resume_summary if profile else None,
            "interview_evaluation": profile.interview_evaluation if profile else None,
            "profile_metadata": profile.profile_metadata if profile else None,
        } if profile else None,
        "current_roadmap": roadmap_out_dict(current) if current else None,
        "latest_daily_report": report_out_dict(daily) if daily else None,
        "latest_weekly_report": report_out_dict(weekly) if weekly else None,
        "final_report": report_out_dict(final) if final else None,
        "insights": build_fresher_insights(daily, current),
    }

@router.get("/freshers/{fresher_id}/roadmaps", response_model=List[RoadmapOut])
def fresher_roadmaps(fresher_id: str, pm: User = Depends(require_pm), db: Session = Depends(get_db)):
    get_assigned_fresher(pm, fresher_id, db)
    rms = db.query(Roadmap).filter(Roadmap.fresher_id == fresher_id).order_by(Roadmap.version.desc()).all()
    return [RoadmapOut(**roadmap_out_dict(r)) for r in rms]

@router.get("/freshers/{fresher_id}/roadmaps/current", response_model=RoadmapOut)
def fresher_current_roadmap(fresher_id: str, pm: User = Depends(require_pm), db: Session = Depends(get_db)):
    get_assigned_fresher(pm, fresher_id, db)
    rm = get_current_roadmap(db, fresher_id)
    if not rm:
        raise HTTPException(status_code=404, detail="No current roadmap")
    return RoadmapOut(**roadmap_out_dict(rm))

@router.get("/freshers/{fresher_id}/reports", response_model=List[ReportOut])
def fresher_reports(fresher_id: str, pm: User = Depends(require_pm), db: Session = Depends(get_db),
                    roadmap_id: Optional[str] = None, limit: int = Query(50, le=500), offset: int = 0):
    get_assigned_fresher(pm, fresher_id, db)
    rows = query_reports(db, fresher_id, None, roadmap_id, None, None, limit, offset)
    return [ReportOut(**report_out_dict(r)) for r in rows]

@router.get("/freshers/{fresher_id}/reports/daily", response_model=List[ReportOut])
def fresher_reports_daily(fresher_id: str, pm: User = Depends(require_pm), db: Session = Depends(get_db),
                          limit: int = Query(50, le=500), offset: int = 0):
    get_assigned_fresher(pm, fresher_id, db)
    rows = query_reports(db, fresher_id, "DAILY", None, None, None, limit, offset)
    return [ReportOut(**report_out_dict(r)) for r in rows]

@router.get("/freshers/{fresher_id}/reports/weekly", response_model=List[ReportOut])
def fresher_reports_weekly(fresher_id: str, pm: User = Depends(require_pm), db: Session = Depends(get_db),
                           limit: int = Query(50, le=500), offset: int = 0):
    get_assigned_fresher(pm, fresher_id, db)
    rows = query_reports(db, fresher_id, "WEEKLY", None, None, None, limit, offset)
    return [ReportOut(**report_out_dict(r)) for r in rows]

@router.get("/freshers/{fresher_id}/reports/final", response_model=List[ReportOut])
def fresher_reports_final(fresher_id: str, pm: User = Depends(require_pm), db: Session = Depends(get_db),
                          limit: int = Query(50, le=500), offset: int = 0):
    get_assigned_fresher(pm, fresher_id, db)
    rows = query_reports(db, fresher_id, "FINAL", None, None, None, limit, offset)
    return [ReportOut(**report_out_dict(r)) for r in rows]

@router.get("/dashboard")
def pm_dashboard(pm: User = Depends(require_pm), db: Session = Depends(get_db)):
    ids = _assigned_fresher_ids(db, pm.id)
    freshers = db.query(User).filter(User.id.in_(ids)).all() if ids else []
    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)

    cards = []
    needing = 0
    reports_this_week = 0
    for f in freshers:
        current = get_current_roadmap(db, f.id)
        daily = _latest_report(db, f.id, "DAILY")
        weekly = _latest_report(db, f.id, "WEEKLY")
        final = _latest_report(db, f.id, "FINAL")

        insights = build_fresher_insights(daily, current)
        needs_human = insights["mentor_required"]
        if needs_human:
            needing += 1

        f_reports = db.query(EvaluationReport).filter(
            EvaluationReport.fresher_id == f.id,
            EvaluationReport.created_at >= week_ago,
        ).count()
        reports_this_week += f_reports

        all_reports = db.query(EvaluationReport).filter(EvaluationReport.fresher_id == f.id)\
            .order_by(EvaluationReport.created_at.desc()).first()
        last_activity = None
        candidates = [r.created_at for r in [daily, weekly, final] if r]
        if current:
            candidates.append(current.updated_at)
        if candidates:
            last_activity = max(candidates)

        cards.append({
            "fresher": _user_out(f),
            "current_roadmap": roadmap_out_dict(current) if current else None,
            "roadmap_progress": (current.completion_pct if current else 0.0),
            "latest_daily_report": report_out_dict(daily) if daily else None,
            "latest_weekly_report": report_out_dict(weekly) if weekly else None,
            "final_report": report_out_dict(final) if final else None,
            # PM dashboard view fields (change #5)
            "strongest_skill": insights["strongest_skill"],
            "current_gap": insights["current_gap"],
            "next_learning_focus": insights["next_learning_focus"],
            "mentor_required": insights["mentor_required"],
            "evidence": insights["evidence"],
            "current_assigned_task": insights["current_assigned_task"],
            "dashboard_update": insights["dashboard_update"],
            # back-compat
            "strengths": insights["strengths"],
            "weaknesses": insights["weaknesses"],
            "needs_human_interaction": needs_human,
            "last_activity_at": last_activity.isoformat() + "Z" if last_activity else None,
        })

    return {
        "pm": _user_out(pm),
        "summary": {
            "assigned_freshers": len(freshers),
            "freshers_needing_interaction": needing,
            "reports_received_this_week": reports_this_week,
        },
        "freshers": cards,
    }
