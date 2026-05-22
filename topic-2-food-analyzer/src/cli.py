"""Command-line interface for the food analyzer."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from src.config import Settings
from src.core.analyzer import MealAnalyzer
from src.storage.repository import repository_from_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="foodanalyzer")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyze a PNG/JPEG meal image.")
    analyze.add_argument("image", help="Path to a PNG/JPEG meal image.")
    analyze.add_argument("--offline", action="store_true", help="Use offline sample providers.")
    analyze.add_argument("--json", action="store_true", help="Print structured JSON.")
    analyze.add_argument("--no-storage", action="store_true", help="Do not write history.")

    history = sub.add_parser("history", help="Show recent analysis records.")
    history.add_argument("--limit", type=int, default=5)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.from_env()
    logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
    if args.command == "analyze":
        if args.offline:
            settings = _replace_settings(settings, offline_mode=True)
        result = asyncio.run(
            MealAnalyzer(settings).analyze(args.image, persist=not args.no_storage)
        )
        if args.json:
            print(result.model_dump_json(indent=2))
        else:
            print(render_result(result))
        return 0
    if args.command == "history":
        records = asyncio.run(repository_from_settings(settings).list_recent(limit=args.limit))
        print(json.dumps([record.model_dump(mode="json") for record in records], indent=2))
        return 0
    return 2


def _replace_settings(settings: Settings, **changes: object) -> Settings:
    data = settings.__dict__.copy()
    data.update(changes)
    return Settings(**data)


def render_result(result) -> str:
    if result.status == "unknown_meal":
        return "Meal not recognized in image."
    headers = ("ingredient", "g", "kcal", "protein", "carbs", "fat", "status")
    body = []
    for row in result.rows:
        ing = row.ingredient
        n = row.nutrition
        body.append(
            (
                ing.name,
                f"{ing.estimated_grams:.0f}",
                f"{n.kcal:.0f}",
                f"{n.protein_g:.1f}",
                f"{n.carbs_g:.1f}",
                f"{n.fat_g:.1f}",
                "ok" if row.error is None else "missing",
            )
        )
    total_grams = sum(row.ingredient.estimated_grams for row in result.rows)
    body.append(
        (
            "TOTAL",
            f"{total_grams:.0f}",
            f"{result.totals.kcal:.0f}",
            f"{result.totals.protein_g:.1f}",
            f"{result.totals.carbs_g:.1f}",
            f"{result.totals.fat_g:.1f}",
            result.status,
        )
    )
    widths = [max(len(headers[i]), max(len(row[i]) for row in body)) for i in range(len(headers))]

    def fmt(row: tuple[str, ...]) -> str:
        return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))

    line = "-" * (sum(widths) + 2 * (len(widths) - 1))
    return "\n".join([fmt(headers), line, *[fmt(row) for row in body[:-1]], line, fmt(body[-1])])


if __name__ == "__main__":
    sys.exit(main())
