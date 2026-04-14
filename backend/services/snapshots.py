from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import calendar
from typing import Iterable

from sqlalchemy.orm import Session

from ..models import Account, BalanceSnapshot

DEBT_TYPES = {"credit_card", "student_loan", "auto_loan", "personal_loan", "mortgage"}


@dataclass
class SnapshotPoint:
    date: str
    net_worth: float


def _month_end(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def _add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def parse_range_start(range_key: str | None, today: date | None = None) -> date | None:
    today = today or date.today()
    key = (range_key or "all").strip().lower()

    if key in {"all", "max"}:
        return None
    if key == "1m":
        return today - timedelta(days=30)
    if key == "3m":
        return today - timedelta(days=90)
    if key == "6m":
        return today - timedelta(days=180)
    if key == "ytd":
        return date(today.year, 1, 1)
    if key == "1y":
        return today - timedelta(days=365)

    return None


def _latest_snapshot_balance(db: Session, account_id: int, as_of: date | None = None) -> float:
    query = db.query(BalanceSnapshot).filter(BalanceSnapshot.account_id == account_id)
    if as_of is not None:
        query = query.filter(BalanceSnapshot.date <= as_of)
    snap = query.order_by(BalanceSnapshot.date.desc()).first()
    return float(snap.balance) if snap else 0.0


def compute_account_balance(db: Session, account: Account, as_of: date | None = None) -> float:
    if account.holdings:
        holdings_total = 0.0
        for h in account.holdings:
            qty = h.quantity or 0
            if h.last_price is not None:
                holdings_total += (h.last_price or 0) * qty
            else:
                holdings_total += float(h.cost_basis or 0)
        return holdings_total

    cash_or_debt = _latest_snapshot_balance(db, account.id, as_of=as_of)
    re_equity = sum((prop.effective_value or 0) - (prop.mortgage_balance or 0) for prop in account.real_estate)
    return float(cash_or_debt + re_equity)


def record_daily_snapshots(db: Session, when: date | None = None) -> dict:
    accounts = db.query(Account).all()
    snap_date = when or date.today()
    recorded = 0

    for account in accounts:
        balance = compute_account_balance(db, account)
        existing = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == account.id, BalanceSnapshot.date == snap_date)
            .first()
        )

        if existing:
            if balance > 0 or existing.balance == 0:
                existing.balance = balance
        else:
            db.add(BalanceSnapshot(account_id=account.id, date=snap_date, balance=balance))
        recorded += 1

    db.commit()
    return {"recorded": recorded, "date": snap_date.isoformat()}


def ensure_month_end_snapshots(db: Session, through: date | None = None) -> dict:
    accounts = db.query(Account).all()
    if not accounts:
        return {"created": 0, "accounts": 0}

    through = through or date.today()
    first_snap = db.query(BalanceSnapshot).order_by(BalanceSnapshot.date.asc()).first()

    if first_snap:
        cursor = _month_end(first_snap.date)
    else:
        cursor = _month_end(through)

    last_month_end = _month_end(through)
    created = 0

    while cursor <= last_month_end:
        for account in accounts:
            exists = (
                db.query(BalanceSnapshot)
                .filter(BalanceSnapshot.account_id == account.id, BalanceSnapshot.date == cursor)
                .first()
            )
            if exists:
                continue

            bal = compute_account_balance(db, account, as_of=cursor)
            if bal == 0 and not account.holdings and not account.real_estate:
                continue

            db.add(BalanceSnapshot(account_id=account.id, date=cursor, balance=bal))
            created += 1

        cursor = _month_end(_add_months(cursor, 1))

    db.commit()
    return {"created": created, "accounts": len(accounts)}


def get_net_worth_history(db: Session, range_key: str | None = None, today: date | None = None) -> list[SnapshotPoint]:
    start = parse_range_start(range_key, today=today)

    query = db.query(BalanceSnapshot)
    if start is not None:
        query = query.filter(BalanceSnapshot.date >= start)

    snapshots: Iterable[BalanceSnapshot] = query.order_by(BalanceSnapshot.date).all()

    by_date: dict[str, float] = {}
    for snap in snapshots:
        key = snap.date.isoformat()
        by_date[key] = by_date.get(key, 0.0) + float(snap.balance)

    return [SnapshotPoint(date=d, net_worth=round(total, 2)) for d, total in sorted(by_date.items())]


def net_worth_overview(db: Session, today: date | None = None) -> dict:
    today = today or date.today()
    accounts = db.query(Account).all()

    total_assets = 0.0
    total_debt = 0.0
    by_type: dict[str, float] = {}

    for account in accounts:
        balance = compute_account_balance(db, account)
        if account.type in DEBT_TYPES:
            total_debt += balance
            by_type[account.type] = round(balance, 2)
        else:
            total_assets += balance
            by_type[account.type] = round(by_type.get(account.type, 0.0) + balance, 2)

    total = total_assets - total_debt

    prior_date = (
        db.query(BalanceSnapshot.date)
        .filter(BalanceSnapshot.date < today)
        .order_by(BalanceSnapshot.date.desc())
        .first()
    )
    previous_total = 0.0
    if prior_date:
        snaps = db.query(BalanceSnapshot).filter(BalanceSnapshot.date == prior_date[0]).all()
        previous_total = sum(float(s.balance) for s in snaps)

    day_30 = today - timedelta(days=30)
    prior_30_date = (
        db.query(BalanceSnapshot.date)
        .filter(BalanceSnapshot.date <= day_30)
        .order_by(BalanceSnapshot.date.desc())
        .first()
    )
    previous_30 = None
    if prior_30_date:
        snaps_30 = db.query(BalanceSnapshot).filter(BalanceSnapshot.date == prior_30_date[0]).all()
        previous_30 = sum(float(s.balance) for s in snaps_30)

    delta = total - previous_total
    delta_30 = None if previous_30 is None else total - previous_30
    delta_30_pct = None
    if previous_30 and previous_30 != 0:
        delta_30_pct = (delta_30 / previous_30) * 100

    by_type["liabilities"] = round(total_debt, 2)

    return {
        "net_worth": round(total, 2),
        "previous": round(previous_total, 2),
        "delta": round(delta, 2),
        "delta_30d": round(delta_30, 2) if delta_30 is not None else None,
        "delta_30d_pct": round(delta_30_pct, 2) if delta_30_pct is not None else None,
        "last_updated": today.isoformat(),
        "by_type": by_type,
    }
