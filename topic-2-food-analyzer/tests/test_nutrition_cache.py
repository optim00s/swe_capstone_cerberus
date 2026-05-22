from __future__ import annotations

import json
import logging
import sys
from types import SimpleNamespace

from ai import NutritionFacts
from src.services.nutrition_cache import CachedNutritionProvider, PostgresCachedNutritionProvider


def test_cache_provider_hit_miss(fake_nutrition, caplog):
    caplog.set_level(logging.INFO, logger="src.services.nutrition_cache")
    cache = CachedNutritionProvider(fake_nutrition, ttl_seconds=60)
    cache.clear()

    facts1 = cache.lookup("broccoli")
    assert facts1.kcal_per_100g == 34
    assert cache.stats.misses == 1
    assert cache.stats.hits == 0

    facts2 = cache.lookup("broccoli")
    assert facts2.kcal_per_100g == 34
    assert cache.stats.misses == 1
    assert cache.stats.hits == 1
    assert "nutrition cache miss backend=memory key=broccoli" in caplog.text
    assert "nutrition cache hit backend=memory key=broccoli" in caplog.text

    cache.clear()
    assert cache.stats.hits == 0
    assert cache.stats.misses == 0


def test_cache_normalization(fake_nutrition):
    cache = CachedNutritionProvider(fake_nutrition, ttl_seconds=60)
    cache.clear()

    facts1 = cache.lookup("  Broccoli  ")
    facts2 = cache.lookup("broccoli")

    assert facts1 == facts2
    assert cache.stats.hits == 1


def test_memory_cache_is_shared_across_provider_instances(fake_nutrition):
    first_cache = CachedNutritionProvider(fake_nutrition, ttl_seconds=60)
    first_cache.clear()
    first_cache.lookup("broccoli")

    second_cache = CachedNutritionProvider(fake_nutrition, ttl_seconds=60)
    second_cache.lookup("broccoli")

    assert first_cache.stats.misses == 1
    assert second_cache.stats.hits == 1
    first_cache.clear()


def test_memory_cache_ttl_zero_bypasses_cache(fake_nutrition):
    cache = CachedNutritionProvider(fake_nutrition, ttl_seconds=0)
    cache.clear()

    cache.lookup("broccoli")
    cache.lookup("broccoli")

    assert cache.stats.misses == 2
    assert cache.stats.hits == 0


def test_postgres_cache_provider_hit_miss(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="src.services.nutrition_cache")
    stored: dict[str, object] = {}
    calls = {"wrapped": 0}

    class CountingNutrition:
        def lookup(self, ingredient_name: str) -> NutritionFacts:
            calls["wrapped"] += 1
            return NutritionFacts(
                name=ingredient_name,
                kcal_per_100g=34,
                protein_g_per_100g=2.8,
                carbs_g_per_100g=7.0,
                fat_g_per_100g=0.4,
                source="fake",
            )

    class FakeConn:
        async def execute(self, sql, *args):
            normalized = " ".join(sql.lower().split())
            if normalized.startswith("insert into nutrition_cache"):
                stored["key"] = args[0]
                stored["facts"] = args[1]
                stored["expires_at"] = args[2]
            if normalized.startswith("delete from nutrition_cache"):
                stored.clear()

        async def fetchrow(self, sql, key):
            del sql
            if stored.get("key") != key:
                return None
            return {"facts": stored["facts"]}

        async def close(self):
            stored["closed"] = True

    async def connect(url):
        assert url == "postgresql://cache-test"
        return FakeConn()

    monkeypatch.setitem(sys.modules, "asyncpg", SimpleNamespace(connect=connect))

    cache = PostgresCachedNutritionProvider(
        CountingNutrition(),
        database_url="postgresql://cache-test",
        ttl_seconds=60,
    )
    first = cache.lookup("  Broccoli  ")
    second = cache.lookup("broccoli")

    assert first == second
    assert json.loads(stored["facts"])["source"] == "fake"
    assert calls["wrapped"] == 1
    assert cache.stats.misses == 1
    assert cache.stats.hits == 1
    assert "nutrition cache miss backend=postgres key=broccoli" in caplog.text
    assert "nutrition cache hit backend=postgres key=broccoli" in caplog.text

    cache.clear()
    assert cache.stats.misses == 0
    assert cache.stats.hits == 0
