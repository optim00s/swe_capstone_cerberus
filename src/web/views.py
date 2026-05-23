"""HTMX view helpers for the food analyzer."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ai.providers.base import ProviderError
from src.config import Settings
from src.models import AnalysisResult


WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATE_DIR = WEB_DIR / "templates"

_templates = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(("html", "xml")),
)


def settings_with_offline(settings: Settings, offline: bool) -> Settings:
    data = settings.__dict__.copy()
    data["offline_mode"] = offline
    return Settings(**data)


def rows_for_table(result: AnalysisResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in result.rows:
        rows.append(
            {
                "ingredient": row.ingredient.name,
                "grams": round(row.ingredient.estimated_grams, 1),
                "kcal": round(row.nutrition.kcal, 1),
                "protein_g": round(row.nutrition.protein_g, 1),
                "carbs_g": round(row.nutrition.carbs_g, 1),
                "fat_g": round(row.nutrition.fat_g, 1),
                "status": "ok" if row.error is None else "missing",
                "source": row.facts.source if row.facts is not None else "",
            }
        )
    return rows


def save_upload_bytes(filename: str, content: bytes, upload_dir: Path) -> Path:
    suffix = Path(filename or "upload.png").suffix.lower()
    stem = Path(filename or "upload").stem or "upload"
    safe_stem = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in stem)
    upload_dir.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix=f"{safe_stem}_",
        suffix=suffix,
        dir=upload_dir,
        delete=False,
    )
    with handle:
        handle.write(content)
    return Path(handle.name)


def render_index_page() -> str:
    return _render("index.html")


def render_analyze_page() -> str:
    return _render("analyze.html")


def render_result_fragment(result: AnalysisResult) -> str:
    if result.status == "unknown_meal":
        return _render("error.html", message="Meal not recognized in the image.", kind="warning")
    return _render("result.html", result=result, rows=rows_for_table(result))


def render_error_fragment(message: str) -> str:
    return _render("error.html", message=message, kind="error")


def provider_error_message(exc: ProviderError) -> str:
    text = str(exc)
    lower = text.lower()
    if "rate limit" in lower or "429" in lower:
        return (
            "Online analysis is temporarily unavailable because the OpenRouter rate "
            "limit was reached. Enable Offline sample mode or try again later."
        )
    if "timeout" in lower or "timed out" in lower:
        return (
            "Online analysis timed out while waiting for the AI provider. "
            "Try again, use a smaller image, or enable Offline sample mode."
        )
    if "usda" in lower:
        return (
            "Nutrition lookup is temporarily unavailable from USDA. "
            "Try again later or enable Offline sample mode for a local demo result."
        )
    return (
        "Online analysis failed while contacting the AI or nutrition provider. "
        "Try again later or enable Offline sample mode."
    )


def _render(template_name: str, **context: object) -> str:
    return _templates.get_template(template_name).render(**context)
