"""
Claude API utility. Use is_configured() before calling chat().
Key is read from env CLAUDE_API_KEY first, then from the DB settings table.
"""
import os
import json
from typing import Optional


def get_api_key() -> Optional[str]:
    key = os.environ.get("CLAUDE_API_KEY")
    if key:
        return key
    return _get_db_key()


def is_configured() -> bool:
    return bool(get_api_key())


def _get_db_key() -> Optional[str]:
    try:
        from .database import SessionLocal
        from .models import Setting
        db = SessionLocal()
        try:
            s = db.query(Setting).get("claude_api_key")
            if s and s.value:
                v = json.loads(s.value)
                return v if isinstance(v, str) and v else None
        finally:
            db.close()
    except Exception:
        return None


async def chat(messages: list[dict], system: str = "") -> str:
    """Call Claude API. Raises ValueError if not configured, httpx errors on failure."""
    import httpx
    key = get_api_key()
    if not key:
        raise ValueError("Claude API key not configured. Add it in Settings.")

    payload: dict = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1024,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
