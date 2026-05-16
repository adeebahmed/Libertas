# backend/tests/test_integration_scheduler.py
import pytest
from unittest.mock import patch, AsyncMock
import os
os.environ.setdefault("PYTEST_CURRENT_TEST", "1")


@pytest.mark.asyncio
async def test_run_daily_sync_once_includes_ofx():
    from backend.services.integration_scheduler import run_daily_sync_once

    with patch("backend.services.integration_scheduler.sync_all_plaid", new_callable=AsyncMock, return_value={}) as mock_plaid, \
         patch("backend.services.integration_scheduler.sync_all_sheets", new_callable=AsyncMock, return_value={}) as mock_sheets, \
         patch("backend.services.integration_scheduler.sync_all_ofx", new_callable=AsyncMock, return_value={"synced": 1, "errors": []}) as mock_ofx:

        result = await run_daily_sync_once(trigger="test")

    mock_ofx.assert_called_once()
    assert "ofx" in result
    assert result["ofx"]["synced"] == 1
