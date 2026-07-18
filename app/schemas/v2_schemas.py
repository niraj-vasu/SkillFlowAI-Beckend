from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime, date

# ---------- Profile ----------
class FresherProfileOut(BaseModel):
    id: str
    user_id: str
    target_role: Optional[str] = None
    joining_date: Optional[date] = None
    resume_summary: Optional[Any] = None
    interview_evaluation: Optional[Any] = None
    current_roadmap_id: Optional[str] = None
    profile_metadata: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

class FresherProfileUpdateIn(BaseModel):
    target_role: Optional[str] = None
    joining_date: Optional[date] = None
    resume_summary: Optional[Any] = None
    interview_evaluation: Optional[Any] = None
    profile_metadata: Optional[Dict[str, Any]] = None

# ---------- Roadmap ----------
class RoadmapCreateIn(BaseModel):
    # Required top-level fields (change #6). client_roadmap_id also drives idempotency (#7).
    client_roadmap_id: str
    title: str
    target_role: str
    start_date: Optional[date] = None
    target_completion_date: Optional[date] = None
    roadmap_payload: Dict[str, Any]

    @field_validator("client_roadmap_id", "title", "target_role")
    @classmethod
    def _nonblank(cls, v):
        if v is None or str(v).strip() == "":
            raise ValueError("field must not be blank")
        return v

    @field_validator("roadmap_payload")
    @classmethod
    def _payload_nonempty(cls, v):
        if not v:
            raise ValueError("roadmap_payload must not be empty")
        return v

class RoadmapProgressIn(BaseModel):
    completion_pct: Optional[float] = None
    status: Optional[str] = None

    @field_validator("completion_pct")
    @classmethod
    def _pct(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("completion_pct must be between 0 and 100")
        return v

    @field_validator("status")
    @classmethod
    def _status(cls, v):
        if v is not None and v not in ("DRAFT", "ACTIVE", "COMPLETED", "ARCHIVED"):
            raise ValueError("invalid status")
        return v

class RoadmapOut(BaseModel):
    id: str
    client_roadmap_id: Optional[str] = None
    fresher_id: str
    version: int
    title: Optional[str] = None
    target_role: Optional[str] = None
    start_date: Optional[date] = None
    target_completion_date: Optional[date] = None
    status: str
    completion_pct: float
    roadmap_payload: Optional[Any] = None
    generated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

# ---------- Reports ----------
class ReportCreateIn(BaseModel):
    client_report_id: str
    roadmap_id: Optional[str] = None
    report_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    overall_score: Optional[float] = None
    needs_human_interaction: bool = False
    report_payload: Dict[str, Any]

    @field_validator("overall_score")
    @classmethod
    def _score(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("overall_score must be between 0 and 100")
        return v

class ReportOut(BaseModel):
    id: str
    client_report_id: str
    fresher_id: str
    roadmap_id: Optional[str] = None
    report_type: str
    schema_version: Optional[str] = None
    report_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    overall_score: Optional[float] = None
    needs_human_interaction: bool = False
    report_payload: Optional[Any] = None
    created_at: datetime
    updated_at: datetime
