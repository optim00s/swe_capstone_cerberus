"""Meal analysis orchestration."""

from __future__ import annotations

import logging

from src.concurrency.pipeline import NutritionLookupPipeline, facts_by_ingredient
from src.config import Settings
from src.models import AnalysisResult, HistoryRecord
from src.services.ai_service import AIService
from src.storage.repository import HistoryRepository, PersistenceError, repository_from_settings
from src.validation import validate_image_path


class MealAnalyzer:
    """Coordinate validation, AI calls, nutrition lookups, totals, and history."""

    def __init__(
        self,
        settings: Settings,
        *,
        service: AIService | None = None,
        repository: HistoryRepository | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger or logging.getLogger(__name__)
        self.service = service or AIService(settings, logger=self.logger)
        self.repository = repository or repository_from_settings(settings)
        self.pipeline = NutritionLookupPipeline(
            self.service,
            max_parallel=settings.max_parallel_lookups,
            logger=self.logger,
        )

    async def analyze(self, image_path: str, *, persist: bool = True) -> AnalysisResult:
        validated = validate_image_path(image_path, max_size_bytes=self.settings.max_image_size_bytes)
        ingredients = await self.service.identify(str(validated))
        if not ingredients:
            result = AnalysisResult(
                status="unknown_meal",
                image_path=str(validated),
                errors=["No recognizable meal was found in the image."],
            )
            await self._save_if_needed(result, persist)
            return result

        rows = await self.pipeline.lookup_all(ingredients)
        facts = facts_by_ingredient(rows)
        totals = self.service.totals(ingredients, facts)
        errors = [row.error for row in rows if row.error]
        result = AnalysisResult(
            status="partial" if errors else "ok",
            image_path=str(validated),
            ingredients=ingredients,
            rows=rows,
            totals=totals,
            errors=errors,
        )
        await self._save_if_needed(result, persist)
        return result

    async def _save_if_needed(self, result: AnalysisResult, persist: bool) -> None:
        if not persist:
            return
        try:
            await self.repository.save(HistoryRecord.from_result(result))
        except PersistenceError as exc:
            self.logger.warning("history persistence unavailable: %s", exc)
