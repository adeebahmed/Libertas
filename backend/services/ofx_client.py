from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from ofxtools.Client import OFXClient, StmtRq, InvStmtRq
from ofxtools.Parser import OFXTree
from ofxtools.utils import UTC

logger = logging.getLogger(__name__)

KNOWN_INSTITUTIONS: dict[str, dict[str, str]] = {
    "fidelity": {
        "url": "https://ofx.fidelity.com/ftgw/OFX/clients/download",
        "fi_id": "7776",
        "org": "fidelity.com",
        "broker_id": "fidelity.com",
    },
}


@dataclass
class OFXConnectionConfig:
    url: str
    fi_id: str
    org: str
    account_number: str
    account_type: str          # CHECKING | SAVINGS | CREDITLINE | INDIVIDUAL | IRA | etc.
    is_investment: bool
    broker_id: Optional[str]   # required for investment accounts


def _fetch_raw_ofx(cfg: OFXConnectionConfig, username: str, password: str, dtstart: datetime.datetime):
    client = OFXClient(
        cfg.url,
        org=cfg.org,
        fid=cfg.fi_id,
        version=220,
        appid="QWIN",
        appver="2700",
    )
    if cfg.is_investment:
        rq = InvStmtRq(
            acctid=cfg.account_number,
            dtstart=dtstart,
            inctran=True,
            incoo=False,
            incpos=True,
            incbal=True,
        )
    else:
        rq = StmtRq(
            acctid=cfg.account_number,
            accttype=cfg.account_type,
            dtstart=dtstart,
            inctran=True,
        )
    with client.request_statements(username, password, rq) as response:
        parser = OFXTree()
        parser.parse(response)
        return parser.convert()


def fetch_ofx_statement(
    cfg: OFXConnectionConfig,
    username: str,
    password: str,
    days_back: int = 90,
) -> list[dict[str, Any]]:
    dtstart = datetime.datetime.now(UTC) - datetime.timedelta(days=days_back)
    ofx = _fetch_raw_ofx(cfg, username, password, dtstart)

    results: list[dict[str, Any]] = []
    for stmt in ofx.statements:
        for tx in stmt.transactions:
            amount = float(tx.trnamt) if isinstance(tx.trnamt, Decimal) else float(tx.trnamt or 0)
            description = tx.name or tx.memo or ""
            results.append(
                {
                    "fitid": tx.fitid,
                    "date": tx.dtposted,
                    "amount": amount,
                    "description": description,
                    "trntype": getattr(tx, "trntype", "other"),
                    "memo": getattr(tx, "memo", None),
                }
            )
    return results
