"""
Auto-ingest engine. Given a file path, this module:
1. Reads the CSV/Excel
2. Analyzes columns to figure out what's what
3. Parses the filename for institution + account type
4. Creates institution/account if needed (or matches existing)
5. Imports all rows with dedup
6. Rebuilds holdings
7. Takes a balance snapshot
8. Logs everything
"""
import os
import csv
import hashlib
import json
import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models import Institution, Account, Transaction, Holding, BalanceSnapshot, ImportLog
from .analyzer import auto_detect_columns, try_parse_date, try_parse_number, normalize_symbol, classify_transaction_type, ColumnRole
from .filename_parser import parse_filename

logger = logging.getLogger(__name__)


def read_file(filepath: str) -> tuple[list[str], list[dict]]:
    """Read a CSV or Excel file, return (headers, rows)."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext in (".xlsx", ".xls"):
        return _read_excel(filepath)
    return _read_csv(filepath)


def _read_csv(filepath: str) -> tuple[list[str], list[dict]]:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        text = f.read()

    lines = text.strip().split("\n")
    # Skip metadata/empty lines — find the header (first line with 2+ commas)
    start = 0
    for i, line in enumerate(lines):
        if line.count(",") >= 2:
            start = i
            break

    reader = csv.DictReader(lines[start:])
    headers = reader.fieldnames or []
    rows = [row for row in reader if any(v.strip() for v in row.values())]
    return headers, rows


def _read_excel(filepath: str) -> tuple[list[str], list[dict]]:
    import openpyxl
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active
    rows_raw = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows_raw:
        return [], []

    # Find header row (first row with multiple non-empty cells)
    header_idx = 0
    for i, row in enumerate(rows_raw):
        non_empty = sum(1 for c in row if c is not None and str(c).strip())
        if non_empty >= 2:
            header_idx = i
            break

    headers = [str(c).strip() if c else f"col_{j}" for j, c in enumerate(rows_raw[header_idx])]
    rows = []
    for row in rows_raw[header_idx + 1:]:
        d = {}
        for j, val in enumerate(row):
            if j < len(headers):
                d[headers[j]] = str(val).strip() if val is not None else ""
        if any(v for v in d.values()):
            rows.append(d)
    return headers, rows


def _compute_row_hash(row: dict, filepath: str) -> str:
    """Hash a row + source file for dedup."""
    raw = json.dumps(row, sort_keys=True, default=str) + "|" + os.path.basename(filepath)
    return hashlib.sha256(raw.encode()).hexdigest()


def _find_or_create_institution(db: Session, name: str) -> Institution:
    """Find existing institution by name (case-insensitive) or create one."""
    existing = db.query(Institution).filter(
        Institution.name.ilike(name)
    ).first()
    if existing:
        return existing

    inst = Institution(name=name)
    db.add(inst)
    db.flush()
    return inst


def _find_or_create_account(db: Session, institution: Institution, account_type: str) -> Account:
    """Find an existing account for this institution+type, or create one."""
    existing = db.query(Account).filter(
        Account.institution_id == institution.id,
        Account.type == account_type,
    ).first()
    if existing:
        return existing

    account = Account(
        name=f"{institution.name} {account_type.replace('_', ' ').title()}",
        type=account_type,
        institution_id=institution.id,
    )
    db.add(account)
    db.flush()
    return account


def _rebuild_holdings(account_id: int, db: Session):
    """Rebuild holdings from all transactions for an account."""
    db.query(Holding).filter(Holding.account_id == account_id).delete()

    txns = db.query(Transaction).filter(Transaction.account_id == account_id).all()
    positions: dict[str, dict] = {}

    for tx in txns:
        if not tx.symbol:
            continue
        sym = tx.symbol.upper().strip()
        if sym not in positions:
            positions[sym] = {"quantity": 0, "cost_basis": 0}

        qty = tx.quantity or 0
        price = tx.price or 0

        if tx.type == "buy":
            positions[sym]["quantity"] += abs(qty)
            positions[sym]["cost_basis"] += abs(qty) * abs(price)
        elif tx.type == "sell":
            positions[sym]["quantity"] -= abs(qty)
        # 'other' types (dividends, fees) don't change position

    for sym, pos in positions.items():
        if abs(pos["quantity"]) < 0.0001:
            continue
        db.add(Holding(
            account_id=account_id,
            symbol=sym,
            quantity=pos["quantity"],
            cost_basis=pos["cost_basis"] if pos["cost_basis"] > 0 else None,
        ))

    db.flush()


def _take_snapshot(account_id: int, db: Session):
    """Snapshot current + historical balances from transaction history."""
    holdings = db.query(Holding).filter(Holding.account_id == account_id).all()
    txns = (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id)
        .order_by(Transaction.date)
        .all()
    )

    # --- Current balance ---
    current_balance = sum(h.cost_basis or 0 for h in holdings)

    if not holdings and txns:
        # Cash account: find most recent Balance column value
        for tx in reversed(txns):
            raw = tx.raw_row or {}
            for k, v in raw.items():
                if "balance" in k.lower():
                    from .analyzer import try_parse_number
                    parsed = try_parse_number(str(v))
                    if parsed is not None:
                        current_balance = parsed
                        break
            if current_balance:
                break

    today = date.today()
    existing = db.query(BalanceSnapshot).filter(
        BalanceSnapshot.account_id == account_id,
        BalanceSnapshot.date == today,
    ).first()
    if existing:
        existing.balance = current_balance
    else:
        db.add(BalanceSnapshot(account_id=account_id, date=today, balance=current_balance))

    # --- Historical monthly snapshots from transaction dates ---
    # Build cumulative cost basis at each transaction date so the chart has history
    if not txns:
        db.flush()
        return

    running: dict[str, float] = {}  # symbol -> quantity * avg_price
    cumulative_cost = 0.0
    cash_balance = 0.0

    seen_months: set[str] = set()
    for tx in txns:
        sym = (tx.symbol or "").upper().strip()
        qty = abs(tx.quantity or 0)
        price = abs(tx.price or 0)
        amount = tx.amount or 0

        if sym and qty:
            if tx.type == "buy":
                running[sym] = running.get(sym, 0) + qty * price
            elif tx.type == "sell":
                running[sym] = max(0, running.get(sym, 0) - qty * price)
            cumulative_cost = sum(running.values())
        else:
            # Cash transaction
            cash_balance += amount

        month_key = tx.date.strftime("%Y-%m")
        if month_key in seen_months:
            continue
        seen_months.add(month_key)

        snap_date = tx.date
        balance_at = cumulative_cost if cumulative_cost > 0 else abs(cash_balance)
        if balance_at <= 0:
            continue

        existing_hist = db.query(BalanceSnapshot).filter(
            BalanceSnapshot.account_id == account_id,
            BalanceSnapshot.date == snap_date,
        ).first()
        if not existing_hist:
            db.add(BalanceSnapshot(account_id=account_id, date=snap_date, balance=round(balance_at, 2)))

    db.flush()


def ingest_file(filepath: str, db: Session) -> ImportLog:
    """
    The main entry point. Ingests a single file fully automatically.
    Returns an ImportLog record describing what happened.
    """
    filename = os.path.basename(filepath)
    log = ImportLog(filename=filename, filepath=filepath)

    try:
        # 1. Read the file
        headers, rows = read_file(filepath)
        if not headers or not rows:
            log.status = "skipped"
            log.error_message = "File is empty or has no data rows"
            db.add(log)
            db.commit()
            return log

        # 2. Detect column roles
        column_map = auto_detect_columns(headers, rows)
        logger.info(f"[{filename}] Detected columns: {column_map}")

        if not column_map:
            log.status = "error"
            log.error_message = "Could not detect any meaningful columns"
            db.add(log)
            db.commit()
            return log

        # 3. Parse filename for institution + account type
        inst_name, account_type = parse_filename(filename)
        logger.info(f"[{filename}] Institution: {inst_name}, Account type: {account_type}")

        # 4. Find or create institution + account
        institution = _find_or_create_institution(db, inst_name)
        account = _find_or_create_account(db, institution, account_type)

        log.institution_name = institution.name
        log.account_id = account.id

        # Flush log early so we get its id for tagging transactions
        db.add(log)
        db.flush()

        # Build reverse map: role -> header
        role_to_header: dict[str, str] = {role: header for header, role in column_map.items()}

        # 5. Import rows
        imported = 0
        skipped = 0

        for row in rows:
            row_hash = _compute_row_hash(row, filepath)
            if db.query(Transaction).filter(Transaction.import_hash == row_hash).first():
                skipped += 1
                continue

            # Extract fields using detected column roles
            date_val = None
            if ColumnRole.DATE in role_to_header:
                parsed = try_parse_date(row.get(role_to_header[ColumnRole.DATE], ""))
                if parsed:
                    date_val = parsed.date()

            symbol_val = None
            if ColumnRole.SYMBOL in role_to_header:
                raw = row.get(role_to_header[ColumnRole.SYMBOL], "").strip()
                if raw:
                    symbol_val = normalize_symbol(raw)

            quantity_val = None
            if ColumnRole.QUANTITY in role_to_header:
                quantity_val = try_parse_number(row.get(role_to_header[ColumnRole.QUANTITY], ""))

            price_val = None
            if ColumnRole.PRICE in role_to_header:
                price_val = try_parse_number(row.get(role_to_header[ColumnRole.PRICE], ""))

            amount_val = None
            if ColumnRole.AMOUNT in role_to_header:
                amount_val = try_parse_number(row.get(role_to_header[ColumnRole.AMOUNT], ""))

            type_val = "buy"
            if ColumnRole.TYPE in role_to_header:
                type_val = classify_transaction_type(row.get(role_to_header[ColumnRole.TYPE], ""))

            desc_val = None
            if ColumnRole.DESCRIPTION in role_to_header:
                desc_val = row.get(role_to_header[ColumnRole.DESCRIPTION], "").strip() or None

            # If we have an amount but no quantity/price, try to infer
            if amount_val and not quantity_val and symbol_val:
                if price_val and price_val != 0:
                    quantity_val = abs(amount_val / price_val)
                else:
                    quantity_val = abs(amount_val)
                    price_val = 1.0

            # Infer type from amount sign if type wasn't detected
            if ColumnRole.TYPE not in role_to_header and amount_val is not None:
                type_val = "buy" if amount_val < 0 else "sell" if amount_val > 0 else "other"

            tx = Transaction(
                account_id=account.id,
                import_log_id=log.id,
                date=date_val or date.today(),
                type=type_val,
                symbol=symbol_val,
                quantity=abs(quantity_val) if quantity_val else None,
                price=abs(price_val) if price_val else None,
                amount=amount_val,
                description=desc_val,
                raw_row=row,
                import_hash=row_hash,
            )
            db.add(tx)
            imported += 1

        db.flush()

        # 6. Rebuild holdings and snapshot
        _rebuild_holdings(account.id, db)
        _take_snapshot(account.id, db)

        log.rows_imported = imported
        log.rows_skipped = skipped
        log.status = "success"
        db.add(log)
        db.commit()

        logger.info(f"[{filename}] Done: {imported} imported, {skipped} skipped")
        return log

    except Exception as e:
        db.rollback()
        log.status = "error"
        log.error_message = str(e)
        db.add(log)
        db.commit()
        logger.exception(f"[{filename}] Ingest failed: {e}")
        return log
