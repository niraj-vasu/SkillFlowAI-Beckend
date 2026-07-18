from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(tags=["system"])

@router.get("/health")
def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "ai_generation": "disabled (frontend-owned)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
