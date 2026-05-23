"""Bounded async nutrition lookup pipeline."""

from __future__ import annotations

import asyncio
import logging

from ai import Ingredient, NutritionFacts
from ai.providers.base import ProviderError

from src.models import IngredientNutrition
from src.services.ai_service import AIService


class NutritionLookupPipeline:
    """Run independent nutrition lookups concurrently with a semaphore."""

    def __init__(
        self,
        service: AIService,
        *,
        max_parallel: int,
        logger: logging.Logger | None = None,
    ) -> None:
        if max_parallel < 1:
            raise ValueError("max_parallel must be >= 1")
        self._service = service
        self._max_parallel = max_parallel
        self._semaphore = asyncio.Semaphore(max_parallel)
        self._logger = logger or logging.getLogger(__name__)

    async def lookup_all(self, ingredients: list[Ingredient]) -> list[IngredientNutrition]:
        self._logger.info(
            "looking up nutrition for %s ingredients with max_parallel=%s",
            len(ingredients),
            self._max_parallel,
        )
        tasks = [self._lookup_one(ingredient) for ingredient in ingredients]
        return list(await asyncio.gather(*tasks))

    async def _lookup_one(self, ingredient: Ingredient) -> IngredientNutrition:
        async with self._semaphore:
            self._logger.info("nutrition lookup started for %s", ingredient.name)
            try:
                facts = await self._service.lookup_nutrition(ingredient.name)
            except ProviderError as exc:
                self._logger.warning("nutrition lookup failed for %s: %s", ingredient.name, exc)
                return IngredientNutrition(ingredient=ingredient, error=str(exc))
            self._logger.info("nutrition lookup finished for %s", ingredient.name)
            return IngredientNutrition(
                ingredient=ingredient,
                facts=facts,
                nutrition=facts.for_grams(ingredient.estimated_grams),
            )


def facts_by_ingredient(rows: list[IngredientNutrition]) -> dict[str, NutritionFacts]:
    return {
        row.ingredient.name: row.facts
        for row in rows
        if row.facts is not None
    }
