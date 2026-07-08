from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from deps import get_db
from services.refresh import refresh_all

router = APIRouter(tags=["admin"])


@router.post("/admin/refresh")
def trigger_refresh(db: Session = Depends(get_db)):
    count = refresh_all(db)
    return {"refreshed_funds": count}
