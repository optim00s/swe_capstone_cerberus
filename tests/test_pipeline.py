from __future__ import annotations

import asyncio
import time

import pytest

from ai import Ingredient, NutritionFacts
from src.concurrency.pipeline import NutritionLookupPipeline
from src.config import Settings
from src.services.ai_service import AIService


@pytest.mark.asyncio
async def test_concurrency_pipeline_ok(fake_nutrition):
    class SlowFakeNutrition(fake_nutrition.__class__):
        async def lookup_nutrition(self, name: str) -> NutritionFacts:
            await asyncio.sleep(0.05)
            return self.lookup(name)

    service = AIService(Settings(offline_mode=True), nutrition_provider=SlowFakeNutrition())
    pipeline = NutritionLookupPipeline(service, max_parallel=2)

    ingredients = [
        Ingredient(name="white rice (cooked)", estimated_grams=100, confidence=0.9),
        Ingredient(name="broccoli", estimated_grams=50, confidence=0.8),
    ]

    start = time.perf_counter()
    rows = await pipeline.lookup_all(ingredients)
    end = time.perf_counter()

    assert len(rows) == 2
    assert all(row.error is None for row in rows)
    assert (end - start) < 0.2


@pytest.mark.asyncio
async def test_concurrency_pipeline_partial_failure(fake_nutrition):
    service = AIService(Settings(offline_mode=True), nutrition_provider=fake_nutrition)
    pipeline = NutritionLookupPipeline(service, max_parallel=2)

    ingredients = [
        Ingredient(name="white rice (cooked)", estimated_grams=100, confidence=0.9),
        Ingredient(name="unknown_ingredient", estimated_grams=50, confidence=0.8),
    ]

    rows = await pipeline.lookup_all(ingredients)

    assert len(rows) == 2
    assert rows[0].error is None
    assert rows[1].error is not None
    assert "unknown ingredient" in rows[1].error.lower()
