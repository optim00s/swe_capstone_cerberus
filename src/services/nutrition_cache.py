"""TTL cache wrapper for synchronous NutritionProvider implementations."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import ModuleType
from typing import Any, Coroutine, TypeVar

from ai import NutritionFacts, NutritionProvider
from ai.providers.base import ProviderError

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CacheProviderError(ProviderError):
    """Raised when the nutrition cache backend fails."""


@dataclass(frozen=True)
class CacheStats:
    hits: int = 0
    misses: int = 0


@dataclass
class _CacheEntry:
    facts: NutritionFacts
    expires_at: float


class CachedNutritionProvider(NutritionProvider):
    """Normalize ingredient names and cache provider lookups for a TTL."""

    _shared_items: dict[str, _CacheEntry] = {}

    def __init__(self, wrapped: NutritionProvider, *, ttl_seconds: int) -> None:
        self._wrapped = wrapped
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0
        self._namespace = f"{wrapped.__class__.__module__}.{wrapped.__class__.__qualname__}"

    @property
    def stats(self) -> CacheStats:
        return CacheStats(hits=self._hits, misses=self._misses)

    def clear(self) -> None:
        keys = [key for key in self._shared_items if key.startswith(f"{self._namespace}:")]
        for key in keys:
            del self._shared_items[key]
        self._hits = 0
        self._misses = 0

    def lookup(self, ingredient_name: str) -> NutritionFacts:
        key = self._key(ingredient_name)
        cache_key = f"{self._namespace}:{key}"
        now = time.monotonic()
        entry = self._shared_items.get(cache_key)
        if entry is not None and entry.expires_at >= now:
            self._hits += 1
            logger.info("nutrition cache hit backend=memory key=%s", key)
            logger.debug("nutrition cache hit payload backend=memory key=%s facts=%s", key, entry.facts.model_dump(mode="json"))
            return entry.facts
        self._misses += 1
        logger.info("nutrition cache miss backend=memory key=%s", key)
        facts = self._wrapped.lookup(key)
        if self._ttl_seconds > 0:
            self._shared_items[cache_key] = _CacheEntry(
                facts=facts,
                expires_at=now + self._ttl_seconds,
            )
            logger.info("nutrition cache write backend=memory key=%s ttl_seconds=%s", key, self._ttl_seconds)
            logger.debug("nutrition cache write payload backend=memory key=%s facts=%s", key, facts.model_dump(mode="json"))
        return facts

    @staticmethod
    def _key(value: str) -> str:
        return " ".join(value.strip().lower().split())


class PostgresCachedNutritionProvider(NutritionProvider):
    """PostgreSQL-backed TTL cache for nutrition lookups.

    The wrapped provider is only called on a miss or expired entry. Values are
    stored as JSONB so the cache survives application process restarts when
    PostgreSQL is kept running.
    """

    def __init__(
        self,
        wrapped: NutritionProvider,
        *,
        database_url: str,
        ttl_seconds: int,
    ) -> None:
        self._wrapped = wrapped
        self._database_url = database_url
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> CacheStats:
        return CacheStats(hits=self._hits, misses=self._misses)

    def clear(self) -> None:
        self._run(self._clear())
        self._hits = 0
        self._misses = 0

    def lookup(self, ingredient_name: str) -> NutritionFacts:
        key = CachedNutritionProvider._key(ingredient_name)
        if self._ttl_seconds <= 0:
            self._misses += 1
            logger.info("nutrition cache bypass backend=postgres key=%s ttl_seconds=%s", key, self._ttl_seconds)
            return self._wrapped.lookup(key)

        cached = self._run(self._read(key))
        if cached is not None:
            self._hits += 1
            logger.info("nutrition cache hit backend=postgres key=%s", key)
            logger.debug("nutrition cache hit payload backend=postgres key=%s facts=%s", key, cached.model_dump(mode="json"))
            return cached

        self._misses += 1
        logger.info("nutrition cache miss backend=postgres key=%s", key)
        facts = self._wrapped.lookup(key)
        self._run(self._write(key, facts))
        logger.info("nutrition cache write backend=postgres key=%s ttl_seconds=%s", key, self._ttl_seconds)
        logger.debug("nutrition cache write payload backend=postgres key=%s facts=%s", key, facts.model_dump(mode="json"))
        return facts

    async def _connect(self) -> Any:
        try:
            import asyncpg
        except ImportError as exc:
            raise CacheProviderError(
                "Install asyncpg to use NUTRITION_CACHE_BACKEND=postgres."
            ) from exc
        try:
            return await asyncpg.connect(self._database_url)
        except _postgres_error_types(asyncpg) as exc:
            raise CacheProviderError(f"Could not connect to PostgreSQL nutrition cache: {exc}") from exc

    async def _ensure_schema(self, conn: Any) -> None:
        await conn.execute(
            """
            create table if not exists nutrition_cache (
                ingredient_key text primary key,
                facts jsonb not null,
                expires_at timestamptz not null,
                updated_at timestamptz not null default now()
            )
            """
        )

    async def _read(self, key: str) -> NutritionFacts | None:
        conn = await self._connect()
        try:
            await self._ensure_schema(conn)
            row = await conn.fetchrow(
                """
                select facts
                from nutrition_cache
                where ingredient_key = $1 and expires_at >= now()
                """,
                key,
            )
        except _postgres_error_types() as exc:
            raise CacheProviderError(f"Could not read PostgreSQL nutrition cache: {exc}") from exc
        finally:
            await _close_connection(conn)
        if row is None:
            return None
        facts = row["facts"]
        if isinstance(facts, str):
            facts = json.loads(facts)
        return NutritionFacts.model_validate(facts)

    async def _write(self, key: str, facts: NutritionFacts) -> None:
        expires_at = datetime.now(UTC) + timedelta(seconds=self._ttl_seconds)
        conn = await self._connect()
        try:
            await self._ensure_schema(conn)
            await conn.execute(
                """
                insert into nutrition_cache (ingredient_key, facts, expires_at, updated_at)
                values ($1, $2::jsonb, $3, now())
                on conflict (ingredient_key) do update set
                    facts = excluded.facts,
                    expires_at = excluded.expires_at,
                    updated_at = now()
                """,
                key,
                json.dumps(facts.model_dump(mode="json")),
                expires_at,
            )
        except _postgres_error_types() as exc:
            raise CacheProviderError(f"Could not write PostgreSQL nutrition cache: {exc}") from exc
        finally:
            await _close_connection(conn)

    async def _clear(self) -> None:
        conn = await self._connect()
        try:
            await self._ensure_schema(conn)
            await conn.execute("delete from nutrition_cache")
        except _postgres_error_types() as exc:
            raise CacheProviderError(f"Could not clear PostgreSQL nutrition cache: {exc}") from exc
        finally:
            await _close_connection(conn)

    @staticmethod
    def _run(coro: Coroutine[Any, Any, T]) -> T:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        coro.close()
        raise RuntimeError(
            "PostgresCachedNutritionProvider.lookup must run outside the active "
            "event-loop thread. Use AIService.lookup_nutrition, which runs it in a worker thread."
        )


def _postgres_error_types(module: ModuleType | Any | None = None) -> tuple[type[BaseException], ...]:
    if module is None:
        try:
            import asyncpg as asyncpg_module
        except ImportError:
            return (OSError, RuntimeError, CacheProviderError)
        module = asyncpg_module
    classes: list[type[BaseException]] = [OSError, RuntimeError, CacheProviderError]
    candidate = getattr(module, "PostgresError", None)
    if isinstance(candidate, type) and issubclass(candidate, BaseException):
        classes.append(candidate)
    return tuple(classes)


async def _close_connection(conn: Any) -> None:
    try:
        await conn.close()
    except _postgres_error_types() as exc:
        raise CacheProviderError(f"Could not close PostgreSQL nutrition cache connection: {exc}") from exc
