import pytest
from datetime import date
from backend.services.source_ingest import source_priority, canonical_key_for


def test_ofx_source_priority_higher_than_sheets():
    assert source_priority("ofx") > source_priority("sheets")


def test_ofx_source_priority_lower_than_plaid():
    assert source_priority("ofx") < source_priority("plaid")


def test_canonical_key_for_ofx_uses_fitid():
    key = canonical_key_for(
        source_kind="ofx",
        external_id="20240101001",
        import_hash=None,
        source_record_id=None,
        account_id=1,
        tx_date=date(2024, 1, 1),
        amount=-50.0,
        description="STARBUCKS",
    )
    assert key == "ofx:20240101001"


def test_canonical_key_for_ofx_without_fitid_falls_back_to_natural():
    key = canonical_key_for(
        source_kind="ofx",
        external_id=None,
        import_hash=None,
        source_record_id=None,
        account_id=1,
        tx_date=date(2024, 1, 1),
        amount=-50.0,
        description="STARBUCKS",
    )
    assert key.startswith("nat:")
