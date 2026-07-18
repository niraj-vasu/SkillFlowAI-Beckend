from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime, time
from ..database import get_db
from ..models.domain import User, FresherProfile, Roadmap, EvaluationReport
from ..schemas.v2_schemas import (
    FresherProfileOut, FresherProfileUpdateIn, RoadmapCreateIn, RoadmapProgressIn,
    RoadmapOut, ReportCreateIn, ReportOut,
)
from .deps import require_fresher
from ..services.report_service import (
    to_dt, next_roadmap_version, find_roadmap_by_client_id, get_current_roadmap,
    roadmap_out_dict, report_out_dict, create_report, query_reports,
)

router = APIRouter(prefix="/api/freshers/me", tags=["fresher"])

def _get_profile(db: Session, user_id: str) -> FresherProfile:
    profile = db.query(FresherProfile).filter(FresherProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Fresher profile not found")
    return profile

# ---------- Profile ----------
@router.get("/profile", response_model=FresherProfileOut)
def get_my_profile(user: User = Depends(require_fresher), db: Session = Depends(get_db)):
    p = _get_profile(db, user.id)
    return FresherProfileOut(
        id=p.id, user_id=p.user_id, target_role=p.target_role,
        joining_date=p.joining_date.date() if p.joining_date else None,
        resume_summary=p.resume_summary, interview_evaluation=p.interview_evaluation,
        current_roadmap_id=p.current_roadmap_id, profile_metadata=p.profile_metadata,
        created_at=p.created_at, updated_at=p.updated_at,
    )

@router.patch("/profile", response_model=FresherProfileOut)
def update_my_profile(body: FresherProfileUpdateIn, user: User = Depends(require_fresher), db: Session = Depends(get_db)):
    p = _get_profile(db, user.id)
    if body.target_role is not None:
        p.target_role = body.target_role
    if body.joining_date is not None:
        p.joining_date = to_dt(body.joining_date)
    if body.resume_summary is not None:
        p.resume_summary = body.resume_summary
    if body.interview_evaluation is not None:
        p.interview_evaluation = body.interview_evaluation
    if body.profile_metadata is not None:
        p.profile_metadata = body.profile_metadata
    db.commit()
    db.refresh(p)
    return FresherProfileOut(
        id=p.id, user_id=p.user_id, target_role=p.target_role,
        joining_date=p.joining_date.date() if p.joining_date else None,
        resume_summary=p.resume_summary, interview_evaluation=p.interview_evaluation,
        current_roadmap_id=p.current_roadmap_id, profile_metadata=p.profile_metadata,
        created_at=p.created_at, updated_at=p.updated_at,
    )

# ---------- Roadmaps ----------
@router.post("/roadmaps", response_model=RoadmapOut, status_code=201)
def create_roadmap(body: RoadmapCreateIn, response: Response, user: User = Depends(require_fresher), db: Session = Depends(get_db)):
    # Idempotency (change #7): same client_roadmap_id returns the existing roadmap (200),
    # not a new version. A new version requires a new client_roadmap_id.
    existing = find_roadmap_by_client_id(db, user.id, body.client_roadmap_id)
    if existing:
        response.status_code = 200
        return RoadmapOut(**roadmap_out_dict(existing))

    version = next_roadmap_version(db, user.id)
    # Archive previously active roadmaps
    for rm in db.query(Roadmap).filter(Roadmap.fresher_id == user.id, Roadmap.status == "ACTIVE").all():
        rm.status = "ARCHIVED"
    roadmap = Roadmap(
        client_roadmap_id=body.client_roadmap_id,
        fresher_id=user.id,
        version=version,
        title=body.title,
        target_role=body.target_role,
        start_date=to_dt(body.start_date),
        target_completion_date=to_dt(body.target_completion_date),
        status="ACTIVE",
        completion_pct=0.0,
        payload=body.roadmap_payload,
    )
    db.add(roadmap)
    db.flush()
    profile = db.query(FresherProfile).filter(FresherProfile.user_id == user.id).first()
    if profile:
        profile.current_roadmap_id = roadmap.id
    db.commit()
    db.refresh(roadmap)
    return RoadmapOut(**roadmap_out_dict(roadmap))

@router.get("/roadmaps", response_model=List[RoadmapOut])
def list_roadmaps(user: User = Depends(require_fresher), db: Session = Depends(get_db)):
    rms = db.query(Roadmap).filter(Roadmap.fresher_id == user.id).order_by(Roadmap.version.desc()).all()
    return [RoadmapOut(**roadmap_out_dict(r)) for r in rms]

@router.get("/roadmaps/current", response_model=RoadmapOut)
def current_roadmap(user: User = Depends(require_fresher), db: Session = Depends(get_db)):
    rm = get_current_roadmap(db, user.id)
    if not rm:
        raise HTTPException(status_code=404, detail="No current roadmap")
    return RoadmapOut(**roadmap_out_dict(rm))

@router.get("/roadmaps/{roadmap_id}", response_model=RoadmapOut)
def get_roadmap(roadmap_id: str, user: User = Depends(require_fresher), db: Session = Depends(get_db)):
    rm = db.query(Roadmap).filter(Roadmap.id == roadmap_id, Roadmap.fresher_id == user.id).first()
    if not rm:
        raise HTTPException(status_code=404, detail=f"Roadmap {roadmap_id} not found")
    return RoadmapOut(**roadmap_out_dict(rm))

@router.patch("/roadmaps/{roadmap_id}/progress", response_model=RoadmapOut)
def update_progress(roadmap_id: str, body: RoadmapProgressIn, user: User = Depends(require_fresher), db: Session = Depends(get_db)):
    rm = db.query(Roadmap).filter(Roadmap.id == roadmap_id, Roadmap.fresher_id == user.id).first()
    if not rm:
        raise HTTPException(status_code=404, detail=f"Roadmap {roadmap_id} not found")
    if body.completion_pct is not None:
        rm.completion_pct = body.completion_pct
    if body.status is not None:
        rm.status = body.status
    db.commit()
    db.refresh(rm)
    return RoadmapOut(**roadmap_out_dict(rm))

@router.post("/roadmaps/{roadmap_id}/complete", response_model=RoadmapOut)
def complete_roadmap(roadmap_id: str, user: User = Depends(require_fresher), db: Session = Depends(get_db)):
    rm = db.query(Roadmap).filter(Roadmap.id == roadmap_id, Roadmap.fresher_id == user.id).first()
    if not rm:
        raise HTTPException(status_code=404, detail=f"Roadmap {roadmap_id} not found")
    rm.status = "COMPLETED"
    rm.completion_pct = 100.0
    db.commit()
    db.refresh(rm)
    return RoadmapOut(**roadmap_out_dict(rm))

# ---------- Reports ----------
def _report_out(r) -> ReportOut:
    return ReportOut(**report_out_dict(r))

@router.post("/reports/daily", response_model=ReportOut)
def create_daily(body: ReportCreateIn, user: User = Depends(require_fresher), db: Session = Depends(get_db)):
    report, _ = create_report(db, user.id, "DAILY", body)
    return _report_out(report)

@router.post("/reports/weekly", response_model=ReportOut)
def create_weekly(body: ReportCreateIn, user: User = Depends(require_fresher), db: Session = Depends(get_db)):
    report, _ = create_report(db, user.id, "WEEKLY", body)
    return _report_out(report)

@router.post("/reports/final", response_model=ReportOut)
def create_final(body: ReportCreateIn, user: User = Depends(require_fresher), db: Session = Depends(get_db)):
    report, _ = create_report(db, user.id, "FINAL", body)
    return _report_out(report)

@router.get("/reports", response_model=List[ReportOut])
def list_reports(
    user: User = Depends(require_fresher), db: Session = Depends(get_db),
    roadmap_id: Optional[str] = None, start_date: Optional[date] = None,
    end_date: Optional[date] = None, limit: int = Query(50, le=500), offset: int = 0,
):
    rows = query_reports(db, user.id, None, roadmap_id, start_date, end_date, limit, offset)
    return [_report_out(r) for r in rows]

@router.get("/reports/daily", response_model=List[ReportOut])
def list_daily(user: User = Depends(require_fresher), db: Session = Depends(get_db),
               roadmap_id: Optional[str] = None, limit: int = Query(50, le=500), offset: int = 0):
    rows = query_reports(db, user.id, "DAILY", roadmap_id, None, None, limit, offset)
    return [_report_out(r) for r in rows]

@router.get("/reports/weekly", response_model=List[ReportOut])
def list_weekly(user: User = Depends(require_fresher), db: Session = Depends(get_db),
                roadmap_id: Optional[str] = None, limit: int = Query(50, le=500), offset: int = 0):
    rows = query_reports(db, user.id, "WEEKLY", roadmap_id, None, None, limit, offset)
    return [_report_out(r) for r in rows]

@router.get("/reports/final", response_model=List[ReportOut])
def list_final(user: User = Depends(require_fresher), db: Session = Depends(get_db),
               roadmap_id: Optional[str] = None, limit: int = Query(50, le=500), offset: int = 0):
    rows = query_reports(db, user.id, "FINAL", roadmap_id, None, None, limit, offset)
    return [_report_out(r) for r in rows]

@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: str, user: User = Depends(require_fresher), db: Session = Depends(get_db)):
    r = db.query(EvaluationReport).filter(
        EvaluationReport.id == report_id, EvaluationReport.fresher_id == user.id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return _report_out(r)
