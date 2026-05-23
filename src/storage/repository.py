"""Analysis history persistence, including a PostgreSQL implementation."""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

from src.config import Settings
from src.models import HistoryRecord


class PersistenceError(RuntimeError):
    """Raised when history persistence fails in a controlled way."""


class HistoryRepository(Protocol):
    async def save(self, record: HistoryRecord) -> None:
        """Persist one analysis record."""

    async def list_recent(self, limit: int = 20) -> list[HistoryRecord]:
        """Return recent records, newest first."""


class NullHistoryRepository:
    async def save(self, record: HistoryRecord) -> None:
        del record

    async def list_recent(self, limit: int = 20) -> list[HistoryRecord]:
        del limit
        return []


class JsonlHistoryRepository:
    """Offline-friendly history store used by tests and demos."""

    def __init__(self, path: Path) -> None:
        self.path = path

    async def save(self, record: HistoryRecord) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(record.model_dump_json() + "\n")
        except OSError as exc:
            raise PersistenceError(f"Could not write JSONL history: {exc}") from exc

    async def list_recent(self, limit: int = 20) -> list[HistoryRecord]:
        try:
            if not self.path.exists():
                return []
            lines = self.path.read_text(encoding="utf-8").splitlines()
            selected = list(reversed(lines[-limit:]))
            return [HistoryRecord.model_validate_json(line) for line in selected if line.strip()]
        except (OSError, ValueError) as exc:
            raise PersistenceError(f"Could not read JSONL history: {exc}") from exc


class PostgresHistoryRepository:
    """PostgreSQL history log backed by asyncpg and jsonb payloads."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    async def save(self, record: HistoryRecord) -> None:
        conn = await self._connect()
        try:
            await self._ensure_schema(conn)
            await conn.execute(
                """
                insert into analysis_history
                    (id, created_at, image_path, status, ingredients, rows, totals, errors)
                values ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb, $8::jsonb)
                on conflict (id) do update set
                    created_at = excluded.created_at,
                    image_path = excluded.image_path,
                    status = excluded.status,
                    ingredients = excluded.ingredients,
                    rows = excluded.rows,
                    totals = excluded.totals,
                    errors = excluded.errors
                """,
                record.id,
                record.created_at,
                record.image_path,
                record.status,
                json.dumps([item.model_dump(mode="json") for item in record.ingredients]),
                json.dumps([item.model_dump(mode="json") for item in record.rows]),
                json.dumps(record.totals.model_dump(mode="json")),
                json.dumps(record.errors),
            )
        except _postgres_error_types() as exc:
            raise PersistenceError(f"Could not write PostgreSQL history: {exc}") from exc
        finally:
            await _close_connection(conn)

    async def list_recent(self, limit: int = 20) -> list[HistoryRecord]:
        conn = await self._connect()
        try:
            await self._ensure_schema(conn)
            rows = await conn.fetch(
                """
                select id, created_at, image_path, status, ingredients, rows, totals, errors
                from analysis_history
                order by created_at desc
                limit $1
                """,
                limit,
            )
        except _postgres_error_types() as exc:
            raise PersistenceError(f"Could not read PostgreSQL history: {exc}") from exc
        finally:
            await _close_connection(conn)
        return [
            HistoryRecord.model_validate(
                {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "image_path": row["image_path"],
                    "status": row["status"],
                    "ingredients": json.loads(row["ingredients"]),
                    "rows": json.loads(row["rows"]),
                    "totals": json.loads(row["totals"]),
                    "errors": json.loads(row["errors"]),
                }
            )
            for row in rows
        ]

    async def _connect(self) -> Any:
        try:
            import asyncpg
        except ImportError as exc:
            raise RuntimeError("Install asyncpg to use STORAGE_BACKEND=postgres.") from exc
        try:
            return await asyncpg.connect(self.database_url)
        except _postgres_error_types(asyncpg) as exc:
            raise PersistenceError(f"Could not connect to PostgreSQL history: {exc}") from exc

    @staticmethod
    async def _ensure_schema(conn: Any) -> None:
        await conn.execute(
            """
            create table if not exists analysis_history (
                id text primary key,
                created_at timestamptz not null,
                image_path text not null,
                status text not null,
                ingredients jsonb not null,
                rows jsonb not null,
                totals jsonb not null,
                errors jsonb not null
            )
            """
        )


def repository_from_settings(settings: Settings) -> HistoryRepository:
    if settings.storage_backend == "none":
        return NullHistoryRepository()
    if settings.storage_backend == "postgres":
        return PostgresHistoryRepository(settings.database_url)
    if settings.storage_backend == "jsonl":
        return JsonlHistoryRepository(settings.history_jsonl_path)
    raise ValueError("STORAGE_BACKEND must be one of: jsonl, postgres, none")


def _postgres_error_types(module: ModuleType | Any | None = None) -> tuple[type[BaseException], ...]:
    if module is None:
        try:
            import asyncpg as asyncpg_module
        except ImportError:
            return (OSError, RuntimeError)
        module = asyncpg_module
    classes: list[type[BaseException]] = [OSError, RuntimeError]
    candidate = getattr(module, "PostgresError", None)
    if isinstance(candidate, type) and issubclass(candidate, BaseException):
        classes.append(candidate)
    return tuple(classes)


async def _close_connection(conn: Any) -> None:
    try:
        await conn.close()
    except _postgres_error_types() as exc:
        raise PersistenceError(f"Could not close PostgreSQL history connection: {exc}") from exc
