from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest

from ai import Nutrition
from src.config import Settings
from src.models import HistoryRecord
from src.storage.repository import PostgresHistoryRepository, repository_from_settings


@pytest.mark.asyncio
async def test_postgres_repository_flow(monkeypatch):
    mock_asyncpg = MagicMock()
    mock_conn = MagicMock()

    async def mock_connect(*args, **kwargs):
        return mock_conn

    async def mock_execute(*args, **kwargs):
        return None

    async def mock_fetch(*args, **kwargs):
        return [
            {
                "id": "1",
                "created_at": datetime.datetime.now(datetime.timezone.utc),
                "image_path": "meal_rice.png",
                "status": "ok",
                "ingredients": "[]",
                "rows": "[]",
                "totals": "{}",
                "errors": "[]",
            }
        ]

    async def mock_close():
        return None

    mock_asyncpg.connect = mock_connect
    mock_conn.execute = mock_execute
    mock_conn.fetch = mock_fetch
    mock_conn.close = mock_close
    monkeypatch.setitem(sys.modules, "asyncpg", mock_asyncpg)

    repo = PostgresHistoryRepository("postgresql://localhost/fake")
    record = HistoryRecord(
        id="1",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        image_path="meal_rice.png",
        status="ok",
        ingredients=[],
        rows=[],
        totals=Nutrition(),
        errors=[],
    )

    await repo.save(record)
    records = await repo.list_recent(limit=5)

    assert len(records) == 1
    assert records[0].id == "1"

    with pytest.raises(ValueError):
        repository_from_settings(Settings(storage_backend="invalid_backend"))


@pytest.mark.asyncio
async def test_postgres_repository_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "asyncpg", None)
    repo = PostgresHistoryRepository("postgresql://localhost/fake")

    with pytest.raises(RuntimeError) as exc:
        await repo.save(None)  # type: ignore[arg-type]

    assert "Install asyncpg" in str(exc.value)
