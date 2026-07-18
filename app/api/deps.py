from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.auth_service import decode_token
from ..models.domain import User, PMFresherAssignment

bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user

def require_fresher(user: User = Depends(get_current_user)) -> User:
    if user.role != "FRESHER":
        raise HTTPException(status_code=403, detail="Fresher role required")
    return user

def require_pm(user: User = Depends(get_current_user)) -> User:
    if user.role != "PM":
        raise HTTPException(status_code=403, detail="PM role required")
    return user

def get_assigned_fresher(pm: User, fresher_id: str, db: Session) -> User:
    fresher = db.query(User).filter(User.id == fresher_id, User.role == "FRESHER").first()
    if not fresher:
        raise HTTPException(status_code=404, detail=f"Fresher {fresher_id} not found")
    assignment = db.query(PMFresherAssignment).filter(
        PMFresherAssignment.pm_user_id == pm.id,
        PMFresherAssignment.fresher_user_id == fresher_id,
        PMFresherAssignment.active == True,
    ).first()
    if not assignment:
        raise HTTPException(status_code=403, detail="Fresher not assigned to you")
    return fresher
