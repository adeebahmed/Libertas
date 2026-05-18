from unittest.mock import patch, MagicMock
from backend.services.ofx_client import OFXConnectionConfig, fetch_ofx_statement


def test_ofx_connection_config_fields():
    cfg = OFXConnectionConfig(
        url="https://ofx.fidelity.com/ftgw/OFX/clients/download",
        fi_id="7776",
        org="fidelity.com",
        account_number="123456789",
        account_type="INDIVIDUAL",
        is_investment=True,
        broker_id="fidelity.com",
    )
    assert cfg.url == "https://ofx.fidelity.com/ftgw/OFX/clients/download"
    assert cfg.is_investment is True


def test_fetch_ofx_statement_bank():
    from decimal import Decimal
    import datetime
    from ofxtools.utils import UTC

    mock_stmt = MagicMock()
    mock_stmt.account.acctid = "CHK123"
    mock_stmt.account.accttype = "CHECKING"
    mock_tx = MagicMock()
    mock_tx.fitid = "20240101001"
    mock_tx.dtposted = datetime.datetime(2024, 1, 1, tzinfo=UTC)
    mock_tx.trnamt = Decimal("-42.50")
    mock_tx.name = "STARBUCKS"
    mock_tx.memo = None
    mock_tx.trntype = "DEBIT"
    mock_stmt.transactions = [mock_tx]

    mock_ofx = MagicMock()
    mock_ofx.statements = [mock_stmt]

    cfg = OFXConnectionConfig(
        url="https://example.com/ofx",
        fi_id="9999",
        org="example.com",
        account_number="CHK123",
        account_type="CHECKING",
        is_investment=False,
        broker_id=None,
    )

    with patch("backend.services.ofx_client._fetch_raw_ofx", return_value=mock_ofx):
        transactions = fetch_ofx_statement(cfg, "user", "pass", days_back=90)

    assert len(transactions) == 1
    tx = transactions[0]
    assert tx["fitid"] == "20240101001"
    assert tx["amount"] == -42.50
    assert tx["description"] == "STARBUCKS"
    assert tx["date"].date().isoformat() == "2024-01-01"
    assert tx["trntype"] == "DEBIT"
