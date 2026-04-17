from __future__ import annotations

import os
from typing import Any, Optional

import httpx

ENV_BASE_URLS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}


class PlaidClient:
    def __init__(
        self,
        client_id: Optional[str] = None,
        secret: Optional[str] = None,
        env: Optional[str] = None,
    ):
        self.env = env or os.getenv("PLAID_ENV", "sandbox")
        self.base_url = ENV_BASE_URLS.get(self.env, os.getenv("PLAID_BASE_URL", "https://sandbox.plaid.com"))
        self.client_id = client_id or os.getenv("PLAID_CLIENT_ID", "")
        self.secret = secret or os.getenv("PLAID_SECRET", "")

    def configured(self) -> bool:
        return bool(self.client_id and self.secret)

    def _body(self, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "client_id": self.client_id,
            "secret": self.secret,
        }
        if extra:
            payload.update(extra)
        return payload

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.configured():
            raise ValueError("Plaid credentials are not configured. Add your Client ID and Secret in Settings → API Keys.")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{self.base_url}{path}", json=self._body(payload))
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = {"error": r.text}
            raise ValueError(f"Plaid API error {r.status_code}: {detail}")
        return r.json()

    async def create_link_token(self, user_id: str, redirect_uri: Optional[str] = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "user": {"client_user_id": user_id},
            "client_name": "Libertas",
            "products": ["transactions", "liabilities"],
            "country_codes": ["US"],
            "language": "en",
        }
        if redirect_uri:
            payload["redirect_uri"] = redirect_uri
        return await self._post("/link/token/create", payload)

    async def exchange_public_token(self, public_token: str) -> dict[str, Any]:
        return await self._post("/item/public_token/exchange", {"public_token": public_token})

    async def get_accounts(self, access_token: str) -> dict[str, Any]:
        return await self._post("/accounts/get", {"access_token": access_token})

    async def get_liabilities(self, access_token: str) -> dict[str, Any]:
        return await self._post("/liabilities/get", {"access_token": access_token})

    async def sync_transactions(self, access_token: str, cursor: Optional[str]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "access_token": access_token,
            "count": 200,
        }
        if cursor:
            payload["cursor"] = cursor

        added: list[dict[str, Any]] = []
        modified: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []

        while True:
            page = await self._post("/transactions/sync", payload)
            added.extend(page.get("added", []))
            modified.extend(page.get("modified", []))
            removed.extend(page.get("removed", []))
            payload["cursor"] = page.get("next_cursor")
            if not page.get("has_more"):
                return {
                    "added": added,
                    "modified": modified,
                    "removed": removed,
                    "next_cursor": page.get("next_cursor"),
                }
