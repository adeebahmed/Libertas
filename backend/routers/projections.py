from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models import Account, Holding, Setting

router = APIRouter(prefix="/api/projections", tags=["projections"])


class ProjectionParams(BaseModel):
    monthly_contribution: float = 0
    years: int = 10
    conservative_rate: float = 0.04
    moderate_rate: float = 0.07
    aggressive_rate: float = 0.10


@router.get("")
def get_projections(
    monthly_contribution: float = 0,
    years: int = 10,
    conservative_rate: float = 0.04,
    moderate_rate: float = 0.07,
    aggressive_rate: float = 0.10,
    db: Session = Depends(get_db),
):
    # Calculate current total balance
    accounts = db.query(Account).all()
    current_balance = 0
    for a in accounts:
        for h in a.holdings:
            current_balance += (h.last_price or 0) * (h.quantity or 0)
        for re in a.real_estate:
            value = re.effective_value or 0
            mortgage = re.mortgage_balance or 0
            current_balance += value - mortgage

    scenarios = {}
    for name, rate in [
        ("conservative", conservative_rate),
        ("moderate", moderate_rate),
        ("aggressive", aggressive_rate),
    ]:
        points = []
        balance = current_balance
        for year in range(years + 1):
            points.append({"year": year, "value": round(balance, 2)})
            # Apply growth and contributions for next year
            balance = balance * (1 + rate) + monthly_contribution * 12
        scenarios[name] = points

    return {
        "current_balance": round(current_balance, 2),
        "params": {
            "monthly_contribution": monthly_contribution,
            "years": years,
            "conservative_rate": conservative_rate,
            "moderate_rate": moderate_rate,
            "aggressive_rate": aggressive_rate,
        },
        "scenarios": scenarios,
    }
