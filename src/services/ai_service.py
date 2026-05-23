"""Retrying, logging AI facade used by CLI, API, and core logic."""

from __future__ import annotations

import asyncio
import logging
import time

from ai import Ingredient, Nutrition, NutritionFacts, NutritionProvider, compute_totals
from ai import get_nutrition_provider, identify_ingredients
from ai.providers.base import VLMProvider

from src.config import Settings
from src.services.nutrition_cache import CachedNutritionProvider, PostgresCachedNutritionProvider
from src.services.offline import OfflineNutritionProvider, OfflineVLM
from src.services.openrouter_provider import OpenRouterVLM
from src.services.rate_limiter import AsyncTokenBucketRateLimiter
from src.services.retry import retry_async


class AIService:
    """Boundary around the provided ai/ package."""

    def __init__(
        self,
        settings: Settings,
        *,
        vlm: VLMProvider | None = None,
        nutrition_provider: NutritionProvider | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger or logging.getLogger(__name__)
        self.vlm = vlm if vlm is not None else self._make_vlm()
        provider = nutrition_provider if nutrition_provider is not None else self._make_nutrition()
        self.nutrition = self._make_cache(provider)
        self.rate_limiter = AsyncTokenBucketRateLimiter(
            capacity=settings.rate_limit_tokens,
            refill_rate_per_second=settings.rate_limit_refill_per_second,
            logger=self.logger,
        )

    async def identify(self, image_path: str) -> list[Ingredient]:
        start = time.perf_counter()

        async def call() -> list[Ingredient]:
            await self.rate_limiter.acquire(label="identify_ingredients")
            return await asyncio.to_thread(identify_ingredients, image_path, vlm=self.vlm)

        self.logger.debug("identify_ingredients input image_path=%s", image_path)
        ingredients = await retry_async(
            call,
            attempts=self.settings.retry_attempts,
            base_delay_seconds=self.settings.retry_base_delay_seconds,
            timeout_seconds=self.settings.ai_timeout_seconds,
            logger=self.logger,
            action="identify_ingredients",
        )
        self.logger.info(
            "identified %s ingredients in %.3fs",
            len(ingredients),
            time.perf_counter() - start,
        )
        self.logger.debug(
            "identify_ingredients output ingredients=%s",
            [ingredient.model_dump(mode="json") for ingredient in ingredients],
        )
        return ingredients

    async def lookup_nutrition(self, ingredient_name: str) -> NutritionFacts:
        async def call() -> NutritionFacts:
            await self.rate_limiter.acquire(label=f"nutrition_lookup:{ingredient_name}")
            return await asyncio.to_thread(self.nutrition.lookup, ingredient_name)

        self.logger.debug("nutrition_lookup input ingredient=%s", ingredient_name)
        facts = await retry_async(
            call,
            attempts=self.settings.retry_attempts,
            base_delay_seconds=self.settings.retry_base_delay_seconds,
            timeout_seconds=self.settings.ai_timeout_seconds,
            logger=self.logger,
            action=f"nutrition_lookup[{ingredient_name}]",
        )
        self.logger.debug("nutrition_lookup output facts=%s", facts.model_dump(mode="json"))
        return facts

    def totals(
        self,
        ingredients: list[Ingredient],
        facts_by_name: dict[str, NutritionFacts],
    ) -> Nutrition:
        return compute_totals(ingredients, facts_by_name)

    def _make_vlm(self) -> VLMProvider | None:
        if self.settings.offline_mode:
            return OfflineVLM()
        if self.settings.uses_openrouter:
            return OpenRouterVLM.from_settings(self.settings)
        return None

    def _make_nutrition(self) -> NutritionProvider:
        if self.settings.offline_mode:
            return OfflineNutritionProvider()
        return get_nutrition_provider()

    def _make_cache(self, provider: NutritionProvider) -> NutritionProvider:
        if self.settings.nutrition_cache_backend == "memory":
            return CachedNutritionProvider(
                provider,
                ttl_seconds=self.settings.nutrition_cache_ttl_seconds,
            )
        if self.settings.nutrition_cache_backend == "postgres":
            return PostgresCachedNutritionProvider(
                provider,
                database_url=self.settings.database_url,
                ttl_seconds=self.settings.nutrition_cache_ttl_seconds,
            )
        if self.settings.nutrition_cache_backend == "none":
            return provider
        raise ValueError("NUTRITION_CACHE_BACKEND must be one of: memory, postgres, none")
