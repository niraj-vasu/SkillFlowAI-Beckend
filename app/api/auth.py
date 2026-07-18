from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.domain import User
from ..schemas.auth_schemas import LoginIn, LoginOut, UserOut
from ..services.auth_service import verify_password, create_access_token
from .deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")
    token = create_access_token(user)
    return LoginOut(
        access_token=token,
        token_type="bearer",
        user=UserOut(id=user.id, email=user.email, name=user.name, role=user.role, is_active=user.is_active),
    )

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role, is_active=user.is_active)
