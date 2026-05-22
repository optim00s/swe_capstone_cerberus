from __future__ import annotations

import pytest

from src.config import Settings
from src.core.analyzer import MealAnalyzer
from src.models import AnalysisResult
from src.services.ai_service import AIService


@pytest.mark.asyncio
async def test_meal_analyzer_happy_path(fake_vlm, fake_nutrition, sample_image):
    settings = Settings(storage_backend="none", offline_mode=True)
    service = AIService(settings, vlm=fake_vlm, nutrition_provider=fake_nutrition)
    analyzer = MealAnalyzer(settings, service=service)

    result = await analyzer.analyze(sample_image, persist=True)

    assert isinstance(result, AnalysisResult)
    assert result.status == "ok"
    assert len(result.rows) == 3
    assert result.totals.kcal > 0


@pytest.mark.asyncio
async def test_meal_analyzer_unknown_meal(fake_vlm, fake_nutrition, sample_image):
    fake_vlm.payload = {"meal_recognized": False, "ingredients": []}
    settings = Settings(storage_backend="none", offline_mode=True)
    service = AIService(settings, vlm=fake_vlm, nutrition_provider=fake_nutrition)
    analyzer = MealAnalyzer(settings, service=service)

    result = await analyzer.analyze(sample_image, persist=False)

    assert isinstance(result, AnalysisResult)
    assert result.status == "unknown_meal"
    assert len(result.rows) == 0
    assert len(result.errors) == 1
