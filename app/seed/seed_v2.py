from sqlalchemy.orm import Session
from datetime import datetime, timezone, date, time
from ..models.domain import (
    User, FresherProfile, PMFresherAssignment, Roadmap, EvaluationReport,
)
from ..services.auth_service import hash_password

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

PM_ID = "USR-PM001"
FRESHER_ID = "USR-F001"
DEMO_PASSWORD = "Demo@123"

def clear_demo_data(db: Session):
    for model in [EvaluationReport, Roadmap, PMFresherAssignment, FresherProfile, User]:
        db.query(model).delete()
    db.commit()

def seed_v2(db: Session):
    # PM
    pm = db.query(User).filter(User.email == "pm@skillflow.local").first()
    if not pm:
        pm = User(id=PM_ID, name="Priya Menon", email="pm@skillflow.local",
                  password_hash=hash_password(DEMO_PASSWORD), role="PM", is_active=True)
        db.add(pm)
        db.flush()

    # Fresher
    fresher = db.query(User).filter(User.email == "fresher@skillflow.local").first()
    if not fresher:
        fresher = User(id=FRESHER_ID, name="Aarav Patel", email="fresher@skillflow.local",
                       password_hash=hash_password(DEMO_PASSWORD), role="FRESHER", is_active=True)
        db.add(fresher)
        db.flush()

    # Assignment (no duplicate active)
    assignment = db.query(PMFresherAssignment).filter(
        PMFresherAssignment.pm_user_id == pm.id,
        PMFresherAssignment.fresher_user_id == fresher.id,
        PMFresherAssignment.active == True,
    ).first()
    if not assignment:
        db.add(PMFresherAssignment(pm_user_id=pm.id, fresher_user_id=fresher.id, active=True))
        db.flush()

    # Fresher profile — an EMPTY real row (no fabricated resume/interview/roadmap content).
    # The frontend fills these in with real data; the dashboard shows only what's actually submitted.
    profile = db.query(FresherProfile).filter(FresherProfile.user_id == fresher.id).first()
    if not profile:
        profile = FresherProfile(
            user_id=fresher.id,
            target_role=None,
            joining_date=None,
            resume_summary=None,
            interview_evaluation=None,
            current_roadmap_id=None,
            profile_metadata=None,
        )
        db.add(profile)
        db.flush()

    # NOTE: no sample roadmap or sample report is seeded. Roadmaps, tasks, and reports are created
    # by the frontend from real onboarding data — the backend never injects placeholder content.

    db.commit()
