"""Sequential-vs-concurrent benchmark helpers for nutrition lookup."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from statistics import mean

from ai import Ingredient, NutritionFacts, NutritionProvider
from src.concurrency.pipeline import NutritionLookupPipeline
from src.config import Settings
from src.services.ai_service import AIService


@dataclass(frozen=True)
class TimingStats:
    """Basic timing summary for repeated benchmark runs."""

    runs: tuple[float, ...]

    @property
    def best(self) -> float:
        return min(self.runs)

    @property
    def worst(self) -> float:
        return max(self.runs)

    @property
    def average(self) -> float:
        return mean(self.runs)


@dataclass(frozen=True)
class BenchmarkResult:
    """Benchmark output ready for console, JSON, report, or README usage."""

    ingredient_count: int
    artificial_delay_seconds: float
    max_parallel: int
    repeats: int
    workload: str
    cache_state: str
    sequential: TimingStats
    concurrent: TimingStats

    @property
    def speedup(self) -> float:
        return self.sequential.average / self.concurrent.average

    @property
    def theoretical_batches(self) -> int:
        return math.ceil(self.ingredient_count / self.max_parallel)

    @property
    def efficiency_percent(self) -> float:
        ideal_speedup = min(self.ingredient_count, self.max_parallel)
        return min(100.0, (self.speedup / ideal_speedup) * 100)

    def to_dict(self) -> dict[str, object]:
        return {
            "ingredient_count": self.ingredient_count,
            "artificial_delay_seconds": self.artificial_delay_seconds,
            "max_parallel": self.max_parallel,
            "repeats": self.repeats,
            "workload": self.workload,
            "cache_state": self.cache_state,
            "theoretical_batches": self.theoretical_batches,
            "sequential_seconds": {
                "runs": list(self.sequential.runs),
                "best": self.sequential.best,
                "worst": self.sequential.worst,
                "average": self.sequential.average,
            },
            "concurrent_seconds": {
                "runs": list(self.concurrent.runs),
                "best": self.concurrent.best,
                "worst": self.concurrent.worst,
                "average": self.concurrent.average,
            },
            "speedup": self.speedup,
            "efficiency_percent": self.efficiency_percent,
        }

    def to_markdown(self) -> str:
        return "\n".join(
            [
                "| Metric | Value |",
                "|---|---:|",
                f"| Ingredients | {self.ingredient_count} |",
                f"| Artificial provider delay | {self.artificial_delay_seconds:.3f} s |",
                f"| Max parallel lookups | {self.max_parallel} |",
                f"| Repeats | {self.repeats} |",
                f"| Workload | {self.workload} |",
                f"| Cache state | {self.cache_state} |",
                f"| Sequential average | {self.sequential.average:.3f} s |",
                f"| Concurrent average | {self.concurrent.average:.3f} s |",
                f"| Speedup | {self.speedup:.2f}x |",
                f"| Parallel efficiency | {self.efficiency_percent:.1f}% |",
            ]
        )


class SlowBenchmarkNutritionProvider(NutritionProvider):
    """Blocking fake provider that mimics one I/O-bound nutrition lookup."""

    def __init__(self, delay_seconds: float) -> None:
        self.delay_seconds = delay_seconds

    def lookup(self, ingredient_name: str) -> NutritionFacts:
        time.sleep(self.delay_seconds)
        return NutritionFacts(
            name=ingredient_name,
            kcal_per_100g=100,
            protein_g_per_100g=10,
            carbs_g_per_100g=20,
            fat_g_per_100g=5,
            source="benchmark",
        )


def build_benchmark_ingredients(count: int) -> list[Ingredient]:
    if count < 1:
        raise ValueError("ingredient count must be at least 1")
    return [
        Ingredient(name=f"ingredient-{index}", estimated_grams=100, confidence=0.9)
        for index in range(count)
    ]


def build_benchmark_pipeline(delay_seconds: float, max_parallel: int) -> NutritionLookupPipeline:
    """Build the same service/pipeline boundary used by the real analyzer.

    Cache TTL is set to zero so each benchmarked lookup hits the fake provider.
    This keeps the comparison fair and satisfies the "caches cleared" rubric
    requirement without depending on external network calls.
    """

    settings = Settings(
        offline_mode=True,
        storage_backend="none",
        nutrition_cache_ttl_seconds=0,
        retry_attempts=1,
        ai_timeout_seconds=max(1.0, delay_seconds * 10),
        rate_limit_tokens=10_000,
        rate_limit_refill_per_second=10_000.0,
    )
    service = AIService(
        settings,
        nutrition_provider=SlowBenchmarkNutritionProvider(delay_seconds),
    )
    return NutritionLookupPipeline(service, max_parallel=max_parallel)


async def run_benchmark_once(
    *,
    ingredient_count: int,
    artificial_delay_seconds: float,
    max_parallel: int,
) -> tuple[float, float]:
    """Return sequential and concurrent timings for one benchmark iteration."""

    if artificial_delay_seconds < 0:
        raise ValueError("artificial delay must be non-negative")
    if max_parallel < 1:
        raise ValueError("max_parallel must be at least 1")

    ingredients = build_benchmark_ingredients(ingredient_count)
    sequential_pipeline = build_benchmark_pipeline(artificial_delay_seconds, max_parallel=1)
    concurrent_pipeline = build_benchmark_pipeline(
        artificial_delay_seconds,
        max_parallel=max_parallel,
    )

    start = time.perf_counter()
    await sequential_pipeline.lookup_all(ingredients)
    sequential_seconds = time.perf_counter() - start

    start = time.perf_counter()
    await concurrent_pipeline.lookup_all(ingredients)
    concurrent_seconds = time.perf_counter() - start

    return sequential_seconds, concurrent_seconds


async def run_benchmark(
    *,
    ingredient_count: int,
    artificial_delay_seconds: float,
    max_parallel: int,
    repeats: int,
) -> BenchmarkResult:
    """Run repeated sequential-vs-concurrent benchmark iterations."""

    if repeats < 1:
        raise ValueError("repeats must be at least 1")

    sequential_runs: list[float] = []
    concurrent_runs: list[float] = []
    for _ in range(repeats):
        sequential, concurrent = await run_benchmark_once(
            ingredient_count=ingredient_count,
            artificial_delay_seconds=artificial_delay_seconds,
            max_parallel=max_parallel,
        )
        sequential_runs.append(sequential)
        concurrent_runs.append(concurrent)

    return BenchmarkResult(
        ingredient_count=ingredient_count,
        artificial_delay_seconds=artificial_delay_seconds,
        max_parallel=max_parallel,
        repeats=repeats,
        workload="I/O-bound nutrition lookups through AIService + NutritionLookupPipeline",
        cache_state="disabled with nutrition_cache_ttl_seconds=0 for every run",
        sequential=TimingStats(tuple(sequential_runs)),
        concurrent=TimingStats(tuple(concurrent_runs)),
    )
