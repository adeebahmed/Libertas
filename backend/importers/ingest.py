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

try:
    import chardet
except ImportError:  # pragma: no cover - fallback when dependency is unavailable
    chardet = None

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


def _decode_csv_bytes(raw: bytes) -> tuple[str, str]:
    """Decode bytes using chardet first, then a small fallback chain."""
    candidates: list[str] = []

    if chardet is not None:
        detected = chardet.detect(raw)
        encoding = detected.get("encoding") if detected else None
        if encoding:
            candidates.append(encoding)

    candidates.extend(["utf-8-sig", "utf-8", "cp1252", "latin-1"])

    seen: set[str] = set()
    for encoding in candidates:
        key = encoding.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            return raw.decode(encoding), encoding
        except (LookupError, UnicodeDecodeError):
            continue

    return raw.decode("latin-1", errors="replace"), "latin-1"


def _read_csv(filepath: str) -> tuple[list[str], list[dict]]:
    with open(filepath, "rb") as f:
        raw = f.read()

    text, _encoding = _decode_csv_bytes(raw)

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return [], []

    # Skip metadata/empty lines — find the header (first line with 2+ commas)
    start = 0
    for i, line in enumerate(lines):
        if line.count(",") >= 2:
            start = i
            break

    reader = csv.DictReader(lines[start:])
    headers = reader.fieldnames or []
    rows = []
    for row in reader:
        normalized = {key: (value or "") for key, value in row.items()}
        if any(value.strip() for value in normalized.values()):
            rows.append(normalized)
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


def _detect_header_drift(
    db: Session,
    account_id: int,
    current_headers: list[str],
    exclude_import_log_id: Optional[int] = None,
) -> dict:
    """Compare the incoming header layout against the latest successful import."""
    filters = [
        ImportLog.account_id == account_id,
        ImportLog.status == "success",
    ]
    if exclude_import_log_id is not None:
        filters.append(ImportLog.id != exclude_import_log_id)

    previous_log = db.query(ImportLog).filter(*filters).order_by(ImportLog.id.desc()).first()

    previous_headers: list[str] = []
    if previous_log:
        previous_tx = (
            db.query(Transaction)
            .filter(Transaction.import_log_id == previous_log.id)
            .order_by(Transaction.id.asc())
            .first()
        )
        if previous_tx and previous_tx.raw_row:
            previous_headers = list(previous_tx.raw_row.keys())

    added = sorted(set(current_headers) - set(previous_headers))
    removed = sorted(set(previous_headers) - set(current_headers))
    order_changed = bool(previous_headers) and previous_headers != current_headers and not added and not removed
    detected = bool(added or removed or order_changed)

    return {
        "detected": detected,
        "added": added,
        "removed": removed,
        "order_changed": order_changed,
        "previous_headers": previous_headers,
        "current_headers": list(current_headers),
    }


def _parse_ingest_row(row: dict, role_to_header: dict[str, str]) -> tuple[dict, list[dict], bool]:
    """Parse a raw row into transaction fields while collecting parse errors."""
    errors: list[dict] = []
    parsed = {
        "date": None,
        "symbol": None,
        "quantity": None,
        "price": None,
        "amount": None,
        "type": "buy",
        "description": None,
    }
    is_transfer = False

    date_header = role_to_header.get(ColumnRole.DATE)
    if date_header:
        raw_date = str(row.get(date_header, "") or "")
        if raw_date.strip():
            parsed_date = try_parse_date(raw_date)
            if parsed_date:
                parsed["date"] = parsed_date.date()
            else:
                errors.append({
                    "field": date_header,
                    "value": raw_date,
                    "message": "Could not parse date",
                })

    symbol_header = role_to_header.get(ColumnRole.SYMBOL)
    if symbol_header:
        raw_symbol = str(row.get(symbol_header, "") or "").strip()
        if raw_symbol:
            parsed["symbol"] = normalize_symbol(raw_symbol)

    quantity_header = role_to_header.get(ColumnRole.QUANTITY)
    if quantity_header:
        raw_quantity = str(row.get(quantity_header, "") or "")
        if raw_quantity.strip():
            quantity_val = try_parse_number(raw_quantity)
            if quantity_val is not None:
                parsed["quantity"] = quantity_val
            else:
                errors.append({
                    "field": quantity_header,
                    "value": raw_quantity,
                    "message": "Could not parse number",
                })

    price_header = role_to_header.get(ColumnRole.PRICE)
    if price_header:
        raw_price = str(row.get(price_header, "") or "")
        if raw_price.strip():
            price_val = try_parse_number(raw_price)
            if price_val is not None:
                parsed["price"] = price_val
            else:
                errors.append({
                    "field": price_header,
                    "value": raw_price,
                    "message": "Could not parse number",
                })

    amount_header = role_to_header.get(ColumnRole.AMOUNT)
    if amount_header:
        raw_amount = str(row.get(amount_header, "") or "")
        if raw_amount.strip():
            amount_val = try_parse_number(raw_amount)
            if amount_val is not None:
                parsed["amount"] = amount_val
            else:
                errors.append({
                    "field": amount_header,
                    "value": raw_amount,
                    "message": "Could not parse number",
                })

    type_header = role_to_header.get(ColumnRole.TYPE)
    if type_header:
        raw_type = str(row.get(type_header, "") or "")
        if raw_type.strip():
            parsed["type"] = classify_transaction_type(raw_type)
            lowered = raw_type.lower()
            if "transfer" in lowered or "xfer" in lowered:
                is_transfer = True
    else:
        raw_type = ""

    desc_header = role_to_header.get(ColumnRole.DESCRIPTION)
    if desc_header:
        raw_desc = str(row.get(desc_header, "") or "").strip()
        if raw_desc:
            parsed["description"] = raw_desc
            lowered = raw_desc.lower()
            if "transfer" in lowered or "xfer" in lowered:
                is_transfer = True

    if parsed["amount"] is not None and not parsed["quantity"] and parsed["symbol"]:
        if parsed["price"] and parsed["price"] != 0:
            parsed["quantity"] = abs(parsed["amount"] / parsed["price"])
        else:
            parsed["quantity"] = abs(parsed["amount"])
            parsed["price"] = 1.0

    if ColumnRole.TYPE not in role_to_header and parsed["amount"] is not None:
        parsed["type"] = "buy" if parsed["amount"] < 0 else "sell" if parsed["amount"] > 0 else "other"

    return parsed, errors, is_transfer


def _detect_transfer_pairs(parsed_rows: list[dict]) -> int:
    """Count matched transfer in/out pairs in the parsed import rows."""
    buckets: dict[tuple, dict[str, int]] = {}

    for row in parsed_rows:
        if not row.get("is_transfer"):
            continue

        amount = row.get("amount")
        if amount is None:
            continue

        key = (
            row.get("date"),
            round(abs(amount), 2),
            (row.get("symbol") or "").upper().strip(),
        )
        bucket = buckets.setdefault(key, {"buy": 0, "sell": 0})
        if row.get("type") == "buy":
            bucket["buy"] += 1
        elif row.get("type") == "sell":
            bucket["sell"] += 1

    return sum(min(bucket["buy"], bucket["sell"]) for bucket in buckets.values())


def _rebuild_holdings(account_id: int, db: Session):
    """Rebuild holdings from all transactions for an account."""
    existing_holdings = db.query(Holding).filter(Holding.account_id == account_id).all()
    txns = db.query(Transaction).filter(Transaction.account_id == account_id).all()
    txn_symbols = {tx.symbol.upper().strip() for tx in txns if tx.symbol and tx.symbol.strip()}
    preserved_holdings = [
        {
            "symbol": holding.symbol,
            "quantity": holding.quantity,
            "cost_basis": holding.cost_basis,
            "last_price": holding.last_price,
            "last_updated": holding.last_updated,
        }
        for holding in existing_holdings
        if holding.symbol and holding.symbol.upper().strip() not in txn_symbols
    ]

    for holding in existing_holdings:
        db.expunge(holding)

    db.query(Holding).filter(Holding.account_id == account_id).delete(synchronize_session=False)

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

    for holding in preserved_holdings:
        db.add(Holding(
            account_id=account_id,
            symbol=holding["symbol"],
            quantity=holding["quantity"],
            cost_basis=holding["cost_basis"],
            last_price=holding["last_price"],
            last_updated=holding["last_updated"],
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

        header_drift = _detect_header_drift(db, account.id, headers, exclude_import_log_id=log.id)
        log.header_drift = header_drift
        log.header_drift_detected = header_drift["detected"]
        log.header_drift_added = header_drift["added"]
        log.header_drift_removed = header_drift["removed"]
        log.header_drift_order_changed = header_drift["order_changed"]

        # Build reverse map: role -> header
        role_to_header: dict[str, str] = {role: header for header, role in column_map.items()}

        # 5. Import rows
        imported = 0
        skipped = 0
        rows_failed = 0
        parse_errors: list[dict] = []
        parsed_rows: list[dict] = []

        for row_index, row in enumerate(rows, start=1):
            row_hash = _compute_row_hash(row, filepath)
            if db.query(Transaction).filter(Transaction.import_hash == row_hash).first():
                skipped += 1
                continue

            parsed_row, row_errors, is_transfer = _parse_ingest_row(row, role_to_header)
            if row_errors:
                rows_failed += 1
                for error in row_errors:
                    parse_errors.append({
                        "row_number": row_index,
                        **error,
                    })

            parsed_row["is_transfer"] = is_transfer
            parsed_rows.append(parsed_row)

            tx = Transaction(
                account_id=account.id,
                import_log_id=log.id,
                date=parsed_row["date"] or date.today(),
                type=parsed_row["type"],
                symbol=parsed_row["symbol"],
                quantity=abs(parsed_row["quantity"]) if parsed_row["quantity"] else None,
                price=abs(parsed_row["price"]) if parsed_row["price"] else None,
                amount=parsed_row["amount"],
                description=parsed_row["description"],
                raw_row=row,
                import_hash=row_hash,
            )
            db.add(tx)
            imported += 1

        db.flush()

        transfer_pairs_detected = _detect_transfer_pairs(parsed_rows)

        # 6. Rebuild holdings and snapshot
        _rebuild_holdings(account.id, db)
        _take_snapshot(account.id, db)

        log.rows_imported = imported
        log.rows_skipped = skipped
        log.rows_failed = rows_failed
        # Store parse error count as scalar for the TEXT column.
        log.parse_errors = str(len(parse_errors))
        log.potential_transfers = transfer_pairs_detected
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
