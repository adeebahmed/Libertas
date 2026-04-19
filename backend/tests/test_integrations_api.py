from backend.routers import integrations


def test_sheets_feed_add_and_status(client):
    account = client.post('/api/accounts', json={"name": "Checking", "type": "checking", "institution_id": None}).json()

    add_resp = client.post(
        '/api/integrations/sheets/add-feed',
        json={
            "name": "Primary Checking Feed",
            "csv_url": "https://docs.google.com/spreadsheets/d/abc/export?format=csv&output=csv",
            "account_id": account["id"],
        },
    )
    assert add_resp.status_code == 200

    status_resp = client.get('/api/integrations/status')
    assert status_resp.status_code == 200
    rows = status_resp.json()["connections"]
    assert len(rows) == 1
    assert rows[0]["provider"] == "sheets"


def test_plaid_exchange_and_disconnect(client, monkeypatch):
    async def fake_exchange(self, public_token: str):
        return {"access_token": "access-sandbox-token", "item_id": "item-123"}

    monkeypatch.setattr(integrations.PlaidClient, "exchange_public_token", fake_exchange)

    exchange_resp = client.post(
        '/api/integrations/plaid/exchange-public-token',
        json={"public_token": "public-sandbox-abc", "name": "Test Plaid"},
    )
    assert exchange_resp.status_code == 200
    body = exchange_resp.json()
    assert body["provider"] == "plaid"
    assert body["status"] == "active"

    disconnect_resp = client.post('/api/integrations/plaid/disconnect', json={"connection_id": body["id"]})
    assert disconnect_resp.status_code == 200
    assert disconnect_resp.json()["status"] == "disabled"


def test_plaid_status_lists_connections(client, monkeypatch):
    async def fake_exchange(self, public_token: str):
        return {"access_token": "access-sandbox-token", "item_id": "item-xyz"}

    monkeypatch.setattr(integrations.PlaidClient, "exchange_public_token", fake_exchange)

    create_resp = client.post(
        '/api/integrations/plaid/exchange-public-token',
        json={"public_token": "public-sandbox-abc", "name": "Primary Plaid"},
    )
    assert create_resp.status_code == 200

    status_resp = client.get('/api/integrations/plaid/status')
    assert status_resp.status_code == 200
    rows = status_resp.json()["connections"]
    assert len(rows) == 1
    assert rows[0]["name"] == "Primary Plaid"
