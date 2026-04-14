from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.snapshots import (
    ensure_month_end_snapshots,
    get_net_worth_history,
    net_worth_overview,
    record_daily_snapshots,
)

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


@router.post("/record")
def record_snapshots(db: Session = Depends(get_db)):
    """Record a net worth snapshot for all accounts for today."""
    return record_daily_snapshots(db)


@router.post("/record-month-end")
def record_month_end_snapshots(
    through: Optional[str] = Query(default=None, description="YYYY-MM-DD date boundary"),
    db: Session = Depends(get_db),
):
    boundary = date.fromisoformat(through) if through else None
    return ensure_month_end_snapshots(db, through=boundary)


@router.get("/net-worth")
def net_worth_history(
    range: Optional[str] = Query(default="all", description="1M|3M|6M|YTD|1Y|ALL"),
    db: Session = Depends(get_db),
):
    """Get net worth over time (aggregated across all accounts)."""
    history = get_net_worth_history(db, range_key=range)
    return [{"date": point.date, "net_worth": point.net_worth} for point in history]


@router.get("/current")
def current_net_worth(db: Session = Depends(get_db)):
    """Get current net worth and deltas."""
    return net_worth_overview(db)
