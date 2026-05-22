"""Probe nutrition cache behavior for one repeated ingredient query."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import Settings
from src.services.ai_service import AIService


async def run_probe(ingredient: str, repeats: int, *, offline: bool) -> dict[str, object]:
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    settings = Settings.from_env()
    if offline:
        settings = _replace_settings(settings, offline_mode=True)
    service = AIService(settings)
    results = []
    for index in range(repeats):
        facts = await service.lookup_nutrition(ingredient)
        results.append(
            {
                "attempt": index + 1,
                "ingredient": ingredient,
                "matched_name": facts.name,
                "source": facts.source,
                "kcal_per_100g": facts.kcal_per_100g,
            }
        )
    stats = getattr(service.nutrition, "stats", None)
    return {
        "cache_backend": settings.nutrition_cache_backend,
        "ttl_seconds": settings.nutrition_cache_ttl_seconds,
        "offline_mode": settings.offline_mode,
        "results": results,
        "cache_stats": None if stats is None else stats.__dict__,
    }


def _replace_settings(settings: Settings, **changes: object) -> Settings:
    data = settings.__dict__.copy()
    data.update(changes)
    return Settings(**data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe repeated nutrition lookup cache behavior.")
    parser.add_argument("--ingredient", default="broccoli")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
    output = asyncio.run(run_probe(args.ingredient, args.repeats, offline=args.offline))
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
