from __future__ import annotations

import pytest

from scripts.cache_probe import run_probe


@pytest.mark.asyncio
async def test_cache_probe_repeats_hit_memory_cache(monkeypatch):
    monkeypatch.setenv("NUTRITION_CACHE_BACKEND", "memory")
    monkeypatch.setenv("NUTRITION_CACHE_TTL_SECONDS", "60")
    result = await run_probe("broccoli", 2, offline=True)

    assert result["cache_backend"] == "memory"
    assert result["cache_stats"] == {"hits": 1, "misses": 1}
    assert result["results"][0]["source"] == "offline"


@pytest.mark.asyncio
async def test_cache_probe_validates_repeats():
    with pytest.raises(ValueError):
        await run_probe("broccoli", 0, offline=True)
