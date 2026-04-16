#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass
class AccountSeed:
    name: str
    kind: str
    institution: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build a deterministic demo DB for landing screenshots.')
    parser.add_argument(
        '--db',
        default=str(ROOT / 'data' / 'libertas-demo.db'),
        help='SQLite path for the generated demo DB',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    os.environ['LIBERTAS_DB_PATH'] = str(db_path)

    from backend.database import SessionLocal, init_db
    from backend.models import (
        Account,
        BalanceSnapshot,
        DebtDetail,
        Holding,
        Institution,
        RealEstate,
        Setting,
        Transaction,
    )

    init_db()

    institutions = [
        'Fidelity',
        'Schwab',
        'Coinbase',
        'Chase',
        'Vanguard',
    ]

    seeds = [
        AccountSeed('Fidelity Brokerage', 'brokerage', 'Fidelity'),
        AccountSeed('Fidelity Roth IRA', 'roth_ira', 'Fidelity'),
        AccountSeed('Schwab Taxable', 'brokerage', 'Schwab'),
        AccountSeed('Schwab IRA', '401k', 'Schwab'),
        AccountSeed('Coinbase Portfolio', 'crypto', 'Coinbase'),
        AccountSeed('Chase Checking', 'checking', 'Chase'),
        AccountSeed('Chase Sapphire', 'credit_card', 'Chase'),
        AccountSeed('Vanguard 401k', '401k', 'Vanguard'),
    ]

    equity_symbols = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'VTI', 'VXUS',
        'QQQ', 'AVUV', 'SCHD', 'VUG', 'JNJ', 'BRK.B', 'TSLA', 'UNH',
    ]
    crypto_symbols = ['BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'MATIC', 'ATOM', 'UNI']

    today = date.today()
    now = datetime.now(timezone.utc)
    random.seed(42)

    db = SessionLocal()
    try:
        inst_map: dict[str, Institution] = {}
        for name in institutions:
            inst = Institution(name=name)
            db.add(inst)
            db.flush()
            inst_map[name] = inst

        accounts: list[Account] = []
        for seed in seeds:
            account = Account(
                name=seed.name,
                type=seed.kind,
                institution_id=inst_map[seed.institution].id,
                currency='USD',
            )
            db.add(account)
            db.flush()
            accounts.append(account)

        real_estate_account = Account(name='Real Estate Assets', type='real_estate', currency='USD')
        db.add(real_estate_account)
        db.flush()

        investment_accounts = [a for a in accounts if a.type in {'brokerage', 'roth_ira', '401k', 'crypto'}]

        # ~40 holdings across investment accounts.
        for idx, account in enumerate(investment_accounts):
            symbols = crypto_symbols if account.type == 'crypto' else equity_symbols[idx * 4:(idx + 1) * 4] + equity_symbols[:4]
            for s_idx, symbol in enumerate(symbols[:8]):
                qty = round(4 + (idx * 1.7) + (s_idx * 0.65), 3)
                base = 35 + (s_idx * 27) + (idx * 11)
                if account.type == 'crypto':
                    base = [64000, 3200, 145, 37, 14, 1.1, 9.6, 7.5][s_idx % 8]
                    qty = round(0.05 + (s_idx * 0.03), 4)
                price = round(base * (1 + random.uniform(-0.14, 0.32)), 2)
                cost_basis = round(qty * base * random.uniform(0.84, 1.06), 2)
                db.add(
                    Holding(
                        account_id=account.id,
                        symbol=symbol,
                        quantity=qty,
                        cost_basis=cost_basis,
                        last_price=price,
                        last_updated=now - timedelta(hours=(idx + s_idx)),
                        source='manual',
                    )
                )

        # 6 months of snapshots for all accounts.
        for account in accounts + [real_estate_account]:
            base_balance = {
                'checking': 14250,
                'credit_card': -4380,
                'real_estate': 0,
                'crypto': 28600,
            }.get(account.type, 124000)
            drift = {
                'checking': 220,
                'credit_card': -85,
                'crypto': 540,
                'real_estate': 0,
            }.get(account.type, 470)

            for week in range(26):
                snapshot_date = today - timedelta(days=(25 - week) * 7)
                wave = random.uniform(-0.028, 0.038)
                balance = base_balance + (week * drift) * (1 + wave)
                if account.type == 'credit_card':
                    balance = min(balance, -900)
                db.add(BalanceSnapshot(account_id=account.id, date=snapshot_date, balance=round(balance, 2)))

        # Debt metadata for debt planning pages.
        cc = next(a for a in accounts if a.type == 'credit_card')
        db.add(DebtDetail(account_id=cc.id, interest_rate=22.9, minimum_payment=165.0, payoff_date=today + timedelta(days=540)))

        # Real estate entries for landing screenshots.
        db.add(
            RealEstate(
                account_id=real_estate_account.id,
                address='2714 Lakeshore Ave, Austin, TX',
                purchase_price=520000,
                purchase_date=today - timedelta(days=1860),
                zillow_estimate=648000,
                manual_override=635000,
                mortgage_balance=341000,
                mortgage_rate=5.75,
                last_updated=now - timedelta(days=2),
            )
        )
        db.add(
            RealEstate(
                account_id=real_estate_account.id,
                address='1489 Palmer St, Denver, CO',
                purchase_price=410000,
                purchase_date=today - timedelta(days=1390),
                zillow_estimate=492000,
                mortgage_balance=278000,
                mortgage_rate=5.2,
                last_updated=now - timedelta(days=3),
            )
        )

        # Transactions for tables/search.
        tx_types = ['buy', 'sell', 'dividend', 'deposit', 'withdrawal', 'payment']
        for account in accounts:
            for n in range(12):
                tx_date = today - timedelta(days=n * 13 + random.randint(0, 8))
                amount_sign = -1 if n % 4 == 0 else 1
                amount = round(amount_sign * random.uniform(120, 2200), 2)
                symbol = None
                if account.type in {'brokerage', 'roth_ira', '401k', 'crypto'} and n % 3 != 0:
                    symbol = random.choice(crypto_symbols if account.type == 'crypto' else equity_symbols)
                tx = Transaction(
                    account_id=account.id,
                    date=tx_date,
                    type=random.choice(tx_types),
                    symbol=symbol,
                    quantity=round(random.uniform(0.2, 12), 4) if symbol else None,
                    price=round(random.uniform(14, 460), 2) if symbol and account.type != 'crypto' else None,
                    amount=amount,
                    description=f'Demo transaction {n + 1} for {account.name}',
                    import_hash=None,
                )
                db.add(tx)

        # Useful defaults for planning pages.
        settings = {
            'monthly_expenses': '6200',
            'risk_profile': 'moderate',
            'income_w2': '168000',
            'income_1099': '24000',
            'tax_filing_status': 'single',
            'birth_year': '1989',
            'retirement_age': '62',
            'monthly_contribution': '3200',
            'retirement_target_amount': '3200000',
        }
        for key, value in settings.items():
            db.add(Setting(key=key, value=value))

        db.commit()
    finally:
        db.close()

    print(f'Demo DB created at: {db_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
