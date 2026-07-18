from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from ..database import Base

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def new_id():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=new_id)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # FRESHER | PM
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class FresherProfile(Base):
    __tablename__ = "fresher_profiles"
    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    target_role = Column(String)
    joining_date = Column(DateTime)
    resume_summary = Column(JSON)
    interview_evaluation = Column(JSON)
    current_roadmap_id = Column(String)
    profile_metadata = Column(JSON)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    user = relationship("User")

class PMFresherAssignment(Base):
    __tablename__ = "pm_fresher_assignments"
    __table_args__ = (UniqueConstraint("pm_user_id", "fresher_user_id", "active", name="uq_active_assignment"),)
    id = Column(String, primary_key=True, default=new_id)
    pm_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    fresher_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    active = Column(Boolean, default=True)
    assigned_at = Column(DateTime, default=utcnow)

class Roadmap(Base):
    __tablename__ = "roadmaps_v2"
    id = Column(String, primary_key=True, default=new_id)
    client_roadmap_id = Column(String)
    fresher_id = Column(String, ForeignKey("users.id"), nullable=False)
    version = Column(Integer, default=1)
    title = Column(String)
    target_role = Column(String)
    start_date = Column(DateTime)
    target_completion_date = Column(DateTime)
    status = Column(String, default="ACTIVE")  # DRAFT | ACTIVE | COMPLETED | ARCHIVED
    completion_pct = Column(Float, default=0.0)
    payload = Column(JSON)
    generated_at = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class EvaluationReport(Base):
    __tablename__ = "evaluation_reports"
    __table_args__ = (UniqueConstraint("client_report_id", name="uq_client_report_id"),)
    id = Column(String, primary_key=True, default=new_id)
    client_report_id = Column(String, nullable=False)
    fresher_id = Column(String, ForeignKey("users.id"), nullable=False)
    roadmap_id = Column(String, ForeignKey("roadmaps_v2.id"))
    report_type = Column(String, nullable=False)  # DAILY | WEEKLY | FINAL
    schema_version = Column(String, default="1.0")
    report_date = Column(DateTime)
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    overall_score = Column(Float)
    needs_human_interaction = Column(Boolean, default=False)
    payload = Column(JSON)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
