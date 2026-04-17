from __future__ import annotations

from datetime import datetime, date
from typing import Any

from sqlalchemy.orm import Session

import json

from ..models import (
    Account,
    BalanceSnapshot,
    DebtDetail,
    IntegrationConnection,
    IntegrationRun,
    Setting,
    Transaction,
)
from .integration_security import decrypt_secret
from .plaid_client import PlaidClient
from .source_ingest import upsert_account_from_source, upsert_transaction


def _plaid_client(db: Session) -> PlaidClient:
    def _get(key: str) -> str:
        row = db.query(Setting).get(key)
        if not row:
            return ""
        try:
            return str(json.loads(row.value))
        except Exception:
            return str(row.value)

    client_id = _get("plaid_client_id")
    secret = _get("plaid_secret")
    env = _get("plaid_env") or None
    return PlaidClient(client_id=client_id or None, secret=secret or None, env=env)


_ASSET_TYPE_MAP = {
    ("depository", "checking"): "checking",
    ("depository", "savings"): "savings",
    ("credit", "credit card"): "credit_card",
    ("loan", "student"): "student_loan",
    ("loan", "auto"): "auto_loan",
    ("loan", "mortgage"): "mortgage",
}


def _account_type_for(acct: dict[str, Any]) -> str:
    t = (acct.get("type") or "").strip().lower()
    st = (acct.get("subtype") or "").strip().lower()
    return _ASSET_TYPE_MAP.get((t, st), "other")


def _transaction_type_for(tx: dict[str, Any]) -> str:
    amount = tx.get("amount")
    if amount is None:
        return "other"
    return "buy" if float(amount) < 0 else "sell" if float(amount) > 0 else "other"


def _parse_tx_date(value: str | None) -> date:
    if not value:
        return date.today()
    return datetime.fromisoformat(value).date()


async def sync_plaid_connection(db: Session, connection: IntegrationConnection, trigger: str = "manual") -> dict[str, Any]:
    run = IntegrationRun(connection_id=connection.id, trigger=trigger, status="running", details={})
    db.add(run)
    db.flush()

    client = _plaid_client(db)
    created = 0
    updated = 0
    deleted = 0

    try:
        access_token = decrypt_secret(connection.encrypted_secret or "")
        accounts_payload = await client.get_accounts(access_token)

        account_map: dict[str, Account] = {}
        for acct in accounts_payload.get("accounts", []):
            account_name = acct.get("name") or acct.get("official_name") or "Plaid Account"
            account = upsert_account_from_source(
                db,
                name=account_name,
                account_type=_account_type_for(acct),
                institution_id=None,
                source_kind="plaid",
                source_record_id=acct.get("account_id"),
                external_id=acct.get("account_id"),
                currency=acct.get("balances", {}).get("iso_currency_code") or "USD",
            )
            account_map[acct.get("account_id", "")] = account

            current_balance = acct.get("balances", {}).get("current")
            if current_balance is not None:
                snap = (
                    db.query(BalanceSnapshot)
                    .filter(BalanceSnapshot.account_id == account.id, BalanceSnapshot.date == date.today())
                    .first()
                )
                if snap:
                    snap.balance = float(current_balance)
                else:
                    db.add(BalanceSnapshot(account_id=account.id, date=date.today(), balance=float(current_balance)))

        txn_payload = await client.sync_transactions(access_token, connection.cursor)
        for tx in txn_payload.get("added", []) + txn_payload.get("modified", []):
            account = account_map.get(tx.get("account_id") or "")
            if not account:
                continue

            _, was_created, _ = upsert_transaction(
                db,
                account_id=account.id,
                tx_date=_parse_tx_date(tx.get("date")),
                tx_type=_transaction_type_for(tx),
                symbol=None,
                quantity=None,
                price=None,
                amount=float(tx.get("amount")) if tx.get("amount") is not None else None,
                description=tx.get("name") or tx.get("merchant_name"),
                source_kind="plaid",
                source_record_id=tx.get("transaction_id"),
                external_id=tx.get("transaction_id"),
                raw_row=tx,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        for tx in txn_payload.get("removed", []):
            q = db.query(Transaction).filter(
                Transaction.external_id == tx.get("transaction_id"),
                Transaction.sync_source == "plaid",
            )
            deleted += q.delete(synchronize_session=False)

        liabilities = await client.get_liabilities(access_token)
        _sync_liabilities(db, liabilities, account_map)

        connection.cursor = txn_payload.get("next_cursor")
        connection.status = "active"
        connection.last_sync_at = datetime.utcnow()
        connection.last_error = None

        run.status = "success"
        run.details = {"created": created, "updated": updated, "deleted": deleted}
    except Exception as exc:
        connection.status = "error"
        connection.last_error = str(exc)
        run.status = "error"
        run.details = {"error": str(exc)}
    finally:
        run.finished_at = datetime.utcnow()
        db.add(connection)
        db.add(run)
        db.commit()

    return {"created": created, "updated": updated, "deleted": deleted, "status": run.status, "error": connection.last_error}


def _sync_liabilities(db: Session, liabilities: dict[str, Any], account_map: dict[str, Account]):
    credit_items = liabilities.get("liabilities", {}).get("credit", [])
    student_items = liabilities.get("liabilities", {}).get("student", [])
    mortgage_items = liabilities.get("liabilities", {}).get("mortgage", [])

    def upsert_detail(account: Account, rate: float | None, min_pay: float | None):
        detail = db.query(DebtDetail).filter(DebtDetail.account_id == account.id).first()
        if not detail:
            detail = DebtDetail(account_id=account.id)
            db.add(detail)
        if rate is not None:
            detail.interest_rate = float(rate)
        if min_pay is not None:
            detail.minimum_payment = float(min_pay)

    for item in credit_items:
        account = account_map.get(item.get("account_id") or "")
        if not account:
            continue
        apr = item.get("aprs", [{}])[0].get("apr_percentage") if item.get("aprs") else None
        upsert_detail(account, apr, item.get("minimum_payment_amount"))

    for item in student_items:
        account = account_map.get(item.get("account_id") or "")
        if not account:
            continue
        upsert_detail(account, item.get("interest_rate_percentage"), item.get("minimum_payment_amount"))

    for item in mortgage_items:
        account = account_map.get(item.get("account_id") or "")
        if not account:
            continue
        upsert_detail(account, item.get("interest_rate", {}).get("percentage"), item.get("last_payment_amount"))


async def sync_all_plaid(db: Session, trigger: str = "scheduled") -> dict[str, Any]:
    connections = db.query(IntegrationConnection).filter(
        IntegrationConnection.provider == "plaid",
        IntegrationConnection.status.in_(["active", "error", "relink_required"]),
    ).all()

    runs = []
    for connection in connections:
        runs.append(await sync_plaid_connection(db, connection, trigger=trigger))
    return {"count": len(connections), "runs": runs}
