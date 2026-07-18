from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..seed.seed_v2 import seed_v2, clear_demo_data

router = APIRouter(prefix="/api/demo", tags=["demo"])

@router.post("/reset")
def reset_demo(db: Session = Depends(get_db)):
    clear_demo_data(db)
    seed_v2(db)
    return {"status": "ok", "message": "Demo data reset successfully"}
