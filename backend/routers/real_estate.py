from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import httpx
from bs4 import BeautifulSoup

from ..database import get_db
from ..models import RealEstate, Account, BalanceSnapshot

router = APIRouter(prefix="/api/real-estate", tags=["real_estate"])


class PropertyCreate(BaseModel):
    account_id: Optional[int] = None
    address: str
    purchase_price: Optional[float] = None
    purchase_date: Optional[date] = None
    mortgage_balance: Optional[float] = None
    mortgage_rate: Optional[float] = None
    manual_override: Optional[float] = None


class PropertyUpdate(BaseModel):
    address: Optional[str] = None
    purchase_price: Optional[float] = None
    purchase_date: Optional[date] = None
    mortgage_balance: Optional[float] = None
    mortgage_rate: Optional[float] = None
    manual_override: Optional[float] = None
    zillow_estimate: Optional[float] = None


@router.get("")
def list_properties(db: Session = Depends(get_db)):
    props = db.query(RealEstate).all()
    return [
        {
            "id": p.id,
            "account_id": p.account_id,
            "address": p.address,
            "purchase_price": p.purchase_price,
            "purchase_date": p.purchase_date.isoformat() if p.purchase_date else None,
            "zillow_estimate": p.zillow_estimate,
            "manual_override": p.manual_override,
            "effective_value": p.effective_value,
            "mortgage_balance": p.mortgage_balance,
            "mortgage_rate": p.mortgage_rate,
            "equity": (p.effective_value or 0) - (p.mortgage_balance or 0),
            "ltv": (p.mortgage_balance or 0) / p.effective_value * 100 if p.effective_value else None,
            "last_updated": p.last_updated.isoformat() if p.last_updated else None,
        }
        for p in props
    ]


@router.post("")
def create_property(data: PropertyCreate, db: Session = Depends(get_db)):
    account_id = data.account_id
    if account_id:
        account = db.query(Account).get(account_id)
        if not account:
            raise HTTPException(404, "Account not found")
    else:
        # Auto-manage a hidden/internal account so users don't need to create/select one.
        account = (
            db.query(Account)
            .filter(Account.type == "real_estate")
            .order_by(Account.id.asc())
            .first()
        )
        if not account:
            account = Account(name="Real Estate Assets", type="real_estate")
            db.add(account)
            db.flush()
        account_id = account.id

    payload = data.model_dump()
    payload["account_id"] = account_id
    prop = RealEstate(**payload)
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.get("/{property_id}")
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = db.query(RealEstate).get(property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    return {
        "id": prop.id,
        "account_id": prop.account_id,
        "address": prop.address,
        "purchase_price": prop.purchase_price,
        "purchase_date": prop.purchase_date.isoformat() if prop.purchase_date else None,
        "zillow_estimate": prop.zillow_estimate,
        "manual_override": prop.manual_override,
        "effective_value": prop.effective_value,
        "mortgage_balance": prop.mortgage_balance,
        "mortgage_rate": prop.mortgage_rate,
        "equity": (prop.effective_value or 0) - (prop.mortgage_balance or 0),
        "ltv": (prop.mortgage_balance or 0) / prop.effective_value * 100 if prop.effective_value else None,
        "last_updated": prop.last_updated.isoformat() if prop.last_updated else None,
    }


@router.patch("/{property_id}")
def update_property(property_id: int, data: PropertyUpdate, db: Session = Depends(get_db)):
    prop = db.query(RealEstate).get(property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(prop, k, v)
    db.commit()
    db.refresh(prop)
    return prop


@router.delete("/{property_id}")
def delete_property(property_id: int, db: Session = Depends(get_db)):
    prop = db.query(RealEstate).get(property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    db.delete(prop)
    db.commit()
    return {"ok": True}


@router.post("/{property_id}/refresh-estimate")
async def refresh_zillow_estimate(property_id: int, db: Session = Depends(get_db)):
    """Attempt to scrape a Zillow/Redfin estimate for the property."""
    prop = db.query(RealEstate).get(property_id)
    if not prop:
        raise HTTPException(404, "Property not found")

    # Attempt Zillow scrape (best effort, may be blocked)
    estimate = await _scrape_zillow(prop.address)
    if estimate:
        prop.zillow_estimate = estimate
        prop.last_updated = datetime.utcnow()
        db.commit()
        return {"estimate": estimate, "source": "zillow"}

    return {"estimate": None, "source": None, "message": "Could not fetch estimate. Use manual override."}


async def _scrape_zillow(address: str) -> Optional[float]:
    """Best-effort Zillow scrape. Returns None if blocked or not found."""
    try:
        query = address.replace(" ", "-").replace(",", "")
        url = f"https://www.zillow.com/homes/{query}_rb/"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                follow_redirects=True,
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "html.parser")
            # Look for Zestimate
            price_el = soup.select_one('[data-testid="zestimate-text"]')
            if price_el:
                text = price_el.get_text().replace("$", "").replace(",", "")
                return float(text)
    except Exception:
        pass
    return None
