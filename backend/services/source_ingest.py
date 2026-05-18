from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from ..models import Account, Transaction

SOURCE_PRIORITY = {
    "manual": 1,
    "sheets": 2,
    "csv": 3,
    "excel": 3,
    "plaid": 4,
}


def source_priority(source_kind: str) -> int:
    return SOURCE_PRIORITY.get(source_kind, 0)


def canonical_key_for(
    *,
    source_kind: str,
    external_id: Optional[str],
    import_hash: Optional[str],
    source_record_id: Optional[str],
    account_id: int,
    tx_date: date,
    amount: Optional[float],
    description: Optional[str],
) -> str:
    if source_kind == "plaid" and external_id:
        return f"plaid:{external_id}"
    if source_kind in {"csv", "excel"} and import_hash:
        return f"file:{import_hash}"
    if source_kind == "sheets" and source_record_id:
        return f"sheets:{source_record_id}"

    payload = {
        "a": account_id,
        "d": tx_date.isoformat(),
        "amt": round(amount or 0, 2),
        "desc": (description or "").strip().lower(),
        "src": source_kind,
        "sid": source_record_id or "",
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return f"nat:{digest}"


def _find_natural_match(
    db: Session,
    *,
    account_id: int,
    tx_date: date,
    amount: Optional[float],
    description: Optional[str],
) -> Optional[Transaction]:
    query = db.query(Transaction).filter(Transaction.account_id == account_id, Transaction.date == tx_date)
    if amount is not None:
        query = query.filter(Transaction.amount == amount)
    candidates = query.order_by(Transaction.id.desc()).limit(10).all()
    normalized_desc = (description or "").strip().lower()
    for candidate in candidates:
        c_desc = (candidate.description or "").strip().lower()
        if normalized_desc and c_desc and normalized_desc != c_desc:
            continue
        return candidate
    return None


def upsert_transaction(
    db: Session,
    *,
    account_id: int,
    tx_date: date,
    tx_type: str,
    symbol: Optional[str],
    quantity: Optional[float],
    price: Optional[float],
    amount: Optional[float],
    description: Optional[str],
    source_kind: str,
    source_record_id: Optional[str] = None,
    external_id: Optional[str] = None,
    import_hash: Optional[str] = None,
    raw_row: Optional[dict] = None,
    import_log_id: Optional[int] = None,
) -> tuple[Transaction, bool, bool]:
    """Upsert one transaction with source precedence.

    Returns: (transaction, created, merged_conflict)
    """
    rank = source_priority(source_kind)
    canonical_key = canonical_key_for(
        source_kind=source_kind,
        external_id=external_id,
        import_hash=import_hash,
        source_record_id=source_record_id,
        account_id=account_id,
        tx_date=tx_date,
        amount=amount,
        description=description,
    )

    tx = db.query(Transaction).filter(Transaction.canonical_key == canonical_key).first()
    merged_conflict = False

    if tx is None:
        natural = _find_natural_match(
            db,
            account_id=account_id,
            tx_date=tx_date,
            amount=amount,
            description=description,
        )
        if natural:
            existing_rank = natural.source_priority or source_priority(natural.source_kind or "")
            if rank >= existing_rank:
                previous_kind = natural.source_kind
                natural.type = tx_type
                natural.symbol = symbol
                natural.quantity = quantity
                natural.price = price
                natural.amount = amount
                natural.description = description
                natural.raw_row = raw_row
                natural.import_log_id = import_log_id
                natural.import_hash = import_hash or natural.import_hash
                natural.external_id = external_id or natural.external_id
                natural.sync_source = source_kind
                natural.source_kind = source_kind
                natural.source_record_id = source_record_id
                natural.source_priority = rank
                natural.canonical_key = canonical_key
                natural.provenance = {
                    "winner": source_kind,
                    "merged_from": previous_kind,
                }
                natural.merge_conflict = 1
                merged_conflict = True
            return natural, False, merged_conflict

    if tx:
        existing_rank = tx.source_priority or source_priority(tx.source_kind or "")
        if rank > existing_rank:
            previous_kind = tx.source_kind
            tx.type = tx_type
            tx.symbol = symbol
            tx.quantity = quantity
            tx.price = price
            tx.amount = amount
            tx.description = description
            tx.raw_row = raw_row
            tx.import_log_id = import_log_id
            tx.import_hash = import_hash or tx.import_hash
            tx.external_id = external_id or tx.external_id
            tx.sync_source = source_kind
            tx.source_kind = source_kind
            tx.source_record_id = source_record_id
            tx.source_priority = rank
            tx.provenance = {
                "winner": source_kind,
                "merged_from": previous_kind,
            }
            tx.merge_conflict = 1
            merged_conflict = True
        return tx, False, merged_conflict

    tx = Transaction(
        account_id=account_id,
        import_log_id=import_log_id,
        date=tx_date,
        type=tx_type,
        symbol=symbol,
        quantity=quantity,
        price=price,
        amount=amount,
        description=description,
        raw_row=raw_row,
        import_hash=import_hash,
        external_id=external_id,
        sync_source=source_kind,
        source_kind=source_kind,
        source_record_id=source_record_id,
        source_priority=rank,
        canonical_key=canonical_key,
        provenance={"winner": source_kind},
        merge_conflict=0,
    )
    db.add(tx)
    return tx, True, merged_conflict


def upsert_account_from_source(
    db: Session,
    *,
    name: str,
    account_type: str,
    institution_id: Optional[int],
    source_kind: str,
    source_record_id: Optional[str] = None,
    external_id: Optional[str] = None,
    currency: str = "USD",
) -> Account:
    account = None
    if external_id:
        account = db.query(Account).filter(Account.external_id == external_id, Account.sync_source == source_kind).first()
    if account is None and source_record_id:
        account = db.query(Account).filter(
            Account.source_kind == source_kind,
            Account.source_record_id == source_record_id,
        ).first()
    if account is None:
        account = db.query(Account).filter(Account.name == name, Account.type == account_type).first()

    rank = source_priority(source_kind)
    if account:
        if rank >= (account.source_priority or 0):
            account.name = name
            account.type = account_type
            account.currency = currency
            account.institution_id = institution_id
            account.sync_source = source_kind
            account.external_id = external_id or account.external_id
            account.source_kind = source_kind
            account.source_record_id = source_record_id
            account.source_priority = rank
        return account

    account = Account(
        name=name,
        type=account_type,
        institution_id=institution_id,
        currency=currency,
        sync_source=source_kind,
        external_id=external_id,
        source_kind=source_kind,
        source_record_id=source_record_id,
        source_priority=rank,
        provenance={"winner": source_kind},
        merge_conflict=0,
    )
    db.add(account)
    db.flush()
    return account
