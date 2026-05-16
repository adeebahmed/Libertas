# backend/tests/test_ofx_router.py
import os
os.environ.setdefault("PYTEST_CURRENT_TEST", "1")
os.environ.setdefault("LIBERTAS_SKIP_DEMO_BOOTSTRAP", "1")
os.environ.setdefault("LIBERTAS_DISABLE_WATCHER", "1")
os.environ.setdefault("LIBERTAS_DISABLE_INTEGRATION_SCHEDULER", "1")

import pytest
from unittest.mock import patch


def _seed_account(client):
    acct = client.post("/api/accounts", json={
        "name": "Checking",
        "type": "checking",
        "institution_id": None,
    }).json()
    return acct["id"]


def test_add_ofx_connection(client):
    acct_id = _seed_account(client)
    with patch("backend.routers.ofx.keyring.set_password") as mock_kc:
        resp = client.post("/api/ofx/connections", json={
            "name": "Fidelity Brokerage",
            "url": "https://ofx.fidelity.com/ftgw/OFX/clients/download",
            "fi_id": "7776",
            "org": "fidelity.com",
            "account_number": "X12345",
            "account_type": "INDIVIDUAL",
            "is_investment": True,
            "broker_id": "fidelity.com",
            "account_id": acct_id,
            "username": "myuser",
            "password": "mypass",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "ofx"
    assert data["name"] == "Fidelity Brokerage"
    mock_kc.assert_called_once()


def test_list_ofx_connections_empty(client):
    resp = client.get("/api/ofx/connections")
    assert resp.status_code == 200
    assert resp.json() == []


def test_sync_now_no_connections(client):
    with patch("backend.routers.ofx.sync_all_ofx", return_value={"synced": 0, "errors": [], "results": []}) as mock_sync:
        resp = client.post("/api/ofx/sync")
    assert resp.status_code == 200
    mock_sync.assert_called_once()


def test_delete_ofx_connection(client):
    acct_id = _seed_account(client)
    with patch("backend.routers.ofx.keyring.set_password"):
        resp = client.post("/api/ofx/connections", json={
            "name": "To Delete",
            "url": "https://example.com/ofx",
            "fi_id": "0001",
            "org": "example.com",
            "account_number": "ACC001",
            "account_type": "CHECKING",
            "is_investment": False,
            "broker_id": None,
            "account_id": acct_id,
            "username": "u",
            "password": "p",
        })
    conn_id = resp.json()["id"]

    with patch("backend.routers.ofx.keyring.delete_password"):
        del_resp = client.delete(f"/api/ofx/connections/{conn_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["ok"] is True
