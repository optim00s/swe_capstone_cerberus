from __future__ import annotations

import json

import pytest

from scripts.bench import format_result
from src.benchmark import build_benchmark_ingredients, run_benchmark


def test_build_benchmark_ingredients_validates_count():
    with pytest.raises(ValueError):
        build_benchmark_ingredients(0)


@pytest.mark.asyncio
async def test_run_benchmark_returns_timing_summary():
    result = await run_benchmark(
        ingredient_count=4,
        artificial_delay_seconds=0.001,
        max_parallel=2,
        repeats=2,
    )

    assert result.ingredient_count == 4
    assert result.max_parallel == 2
    assert result.repeats == 2
    assert result.theoretical_batches == 2
    assert "AIService" in result.workload
    assert "ttl_seconds=0" in result.cache_state
    assert len(result.sequential.runs) == 2
    assert len(result.concurrent.runs) == 2
    assert result.sequential.average > 0
    assert result.concurrent.average > 0
    assert result.speedup > 0


@pytest.mark.asyncio
async def test_run_benchmark_rejects_invalid_arguments():
    with pytest.raises(ValueError):
        await run_benchmark(
            ingredient_count=1,
            artificial_delay_seconds=0,
            max_parallel=1,
            repeats=0,
        )

    with pytest.raises(ValueError):
        await run_benchmark(
            ingredient_count=1,
            artificial_delay_seconds=-1,
            max_parallel=1,
            repeats=1,
        )

    with pytest.raises(ValueError):
        await run_benchmark(
            ingredient_count=1,
            artificial_delay_seconds=0,
            max_parallel=0,
            repeats=1,
        )


@pytest.mark.asyncio
async def test_benchmark_formats_json_and_markdown():
    result = await run_benchmark(
        ingredient_count=2,
        artificial_delay_seconds=0,
        max_parallel=2,
        repeats=1,
    )

    as_json = json.loads(format_result(result, "json"))
    assert as_json["ingredient_count"] == 2
    assert as_json["cache_state"] == "disabled with nutrition_cache_ttl_seconds=0 for every run"
    assert "speedup" in as_json

    as_markdown = format_result(result, "markdown")
    assert "| Metric | Value |" in as_markdown
    assert "Speedup" in as_markdown
    assert "Cache state" in as_markdown

    as_text = format_result(result, "text")
    assert "speedup=" in as_text
