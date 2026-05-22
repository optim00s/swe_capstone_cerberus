from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai import Ingredient, NutritionFacts, Nutrition
from src.api import app
from src.config import Settings
from src.cli import main, render_result
from src.validation import ImageValidationError, validate_image_path, media_type_for_path
from src.storage.repository import JsonlHistoryRepository, NullHistoryRepository
from src.models import AnalysisResult, IngredientNutrition
from src.web.views import render_error_fragment, render_result_fragment


PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000"
    "00907753de0000000c4944415408d76360000000000004000146a13a"
    "020000000049454e44ae426082"
)


# --- 1. Image Validation Tests ---

def test_validate_image_accepts_png(tmp_path: Path):
    image = tmp_path / "meal.png"
    image.write_bytes(PNG_BYTES)
    assert validate_image_path(image, max_size_bytes=1024) == image


def test_validate_image_rejects_wrong_magic(tmp_path: Path):
    image = tmp_path / "meal.png"
    image.write_bytes(b"not a png")
    with pytest.raises(ImageValidationError):
        validate_image_path(image, max_size_bytes=1024)


def test_validate_image_rejects_large_file(tmp_path: Path):
    image = tmp_path / "meal.png"
    image.write_bytes(PNG_BYTES)
    with pytest.raises(ImageValidationError):
        validate_image_path(image, max_size_bytes=4)


def test_media_type_for_path():
    assert media_type_for_path("meal.png") == "image/png"
    assert media_type_for_path("meal.jpeg") == "image/jpeg"
    with pytest.raises(ImageValidationError):
        media_type_for_path("meal.gif")


# --- 2. Configuration Layer Tests ---

def test_settings_from_env_reads_openrouter(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("MAX_PARALLEL_LOOKUPS", "4")
    monkeypatch.setenv("RATE_LIMIT_TOKENS", "6")
    monkeypatch.setenv("RATE_LIMIT_REFILL_PER_SECOND", "2.5")
    settings = Settings.from_env(load_dotenv=False)
    assert settings.uses_openrouter is True
    assert settings.openrouter_api_key == "test-key"
    assert settings.max_parallel_lookups == 4
    assert settings.rate_limit_tokens == 6
    assert settings.rate_limit_refill_per_second == 2.5


def test_settings_validates_positive_numbers(monkeypatch):
    monkeypatch.setenv("MAX_PARALLEL_LOOKUPS", "0")
    with pytest.raises(ValueError):
        Settings.from_env(load_dotenv=False)


# --- 3. FastAPI Web Endpoint Tests ---

def test_api_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_root_redirects_to_ui():
    client = TestClient(app, follow_redirects=False)
    response = client.get("/")
    assert response.status_code == 307
    assert response.headers["location"] == "/ui"


def test_api_favicon():
    client = TestClient(app)
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in response.content


def test_api_ui_index():
    client = TestClient(app)
    response = client.get("/ui")
    assert response.status_code == 200
    assert "NutriSnap AI" in response.text
    assert 'class="home-page"' in response.text
    assert "/static/logo.svg?v=20260520-4" in response.text
    assert "/static/styles.css?v=20260520-4" in response.text
    assert "/static/preview.js?v=20260520-4" in response.text
    assert "Created by Cerberus" in response.text
    assert "https://github.com/optim00s/" in response.text
    assert "https://www.aiacademy.az/" in response.text
    assert "nav-links" not in response.text


def test_api_ui_analyze_page():
    client = TestClient(app)
    response = client.get("/ui/analyze-page")
    assert response.status_code == 200
    assert "Nutrition Analyzer" in response.text
    assert 'hx-post="/ui/analyze"' in response.text
    assert "/static/logo.svg?v=20260520-4" in response.text
    assert "/static/styles.css?v=20260520-4" in response.text
    assert "/static/preview.js?v=20260520-4" in response.text
    assert 'hx-indicator=".analysis-indicator"' in response.text
    assert "loading-results" in response.text
    assert "skeleton-card" in response.text
    assert "Created by Cerberus" in response.text
    assert "nav-links" not in response.text


def test_api_analyze_endpoint(monkeypatch, sample_image):
    # Set settings to offline mode
    monkeypatch.setenv("OFFLINE_MODE", "True")
    monkeypatch.setenv("STORAGE_BACKEND", "none")
    
    client = TestClient(app)
    with open(sample_image, "rb") as f:
        response = client.post(
            "/analyze",
            files={"file": ("meal_rice_chicken_broccoli.png", f, "image/png")},
            data={"offline": "true"}
        )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert data["result"]["status"] == "ok"


def test_api_ui_analyze_endpoint_htmx(monkeypatch, sample_image):
    # Set settings to offline mode
    monkeypatch.setenv("OFFLINE_MODE", "True")
    monkeypatch.setenv("STORAGE_BACKEND", "none")
    
    client = TestClient(app)
    with open(sample_image, "rb") as f:
        response = client.post(
            "/ui/analyze",
            files={"file": ("meal_rice_chicken_broccoli.png", f, "image/png")},
            data={"offline": "true", "persist": "false"}
        )
    assert response.status_code == 200
    assert "Energy" in response.text
    assert "Protein" in response.text


# --- 4. CLI Command Tests ---

def test_cli_analyze_happy_path(monkeypatch, sample_image, capsys):
    monkeypatch.setenv("OFFLINE_MODE", "True")
    monkeypatch.setenv("STORAGE_BACKEND", "none")
    
    exit_code = main(["analyze", sample_image, "--offline", "--no-storage"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "white rice" in captured.out
    assert "TOTAL" in captured.out


def test_cli_analyze_json(monkeypatch, sample_image, capsys):
    monkeypatch.setenv("OFFLINE_MODE", "True")
    monkeypatch.setenv("STORAGE_BACKEND", "none")
    
    exit_code = main(["analyze", sample_image, "--offline", "--no-storage", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "status" in data
    assert data["status"] == "ok"


# --- 5. Storage Repository Tests ---

@pytest.mark.asyncio
async def test_jsonl_repository_flow(tmp_path: Path):
    path = tmp_path / "test_history.jsonl"
    repo = JsonlHistoryRepository(path)
    
    # Save a record
    record = AnalysisResult(
        status="ok",
        image_path="dummy.png",
        ingredients=[],
        rows=[],
        totals=Nutrition(),
        errors=[],
    )
    
    await repo.save(record)
    assert path.exists()
    
    # List recent
    records = await repo.list_recent(limit=5)
    assert len(records) == 1
    assert records[0].image_path == "dummy.png"


@pytest.mark.asyncio
async def test_null_repository_flow():
    repo = NullHistoryRepository()
    record = AnalysisResult(
        status="ok",
        image_path="dummy.png",
        ingredients=[],
        rows=[],
        totals=Nutrition(),
        errors=[],
    )
    await repo.save(record)
    records = await repo.list_recent()
    assert records == []


# --- 6. HTML Rendering Views Tests ---

def test_render_error_fragment():
    html = render_error_fragment("This is a bad request")
    assert "notice-box" in html
    assert "error-box" in html
    assert "This is a bad request" in html


def test_render_result_fragment():
    result = AnalysisResult(
        status="ok",
        image_path="dummy.png",
        ingredients=[],
        rows=[
            IngredientNutrition(
                ingredient=Ingredient(name="rice", estimated_grams=100, confidence=0.9),
                facts=NutritionFacts(name="rice", kcal_per_100g=130, protein_g_per_100g=2.7, carbs_g_per_100g=28, fat_g_per_100g=0.3, source="fake"),
                nutrition=Nutrition(kcal=130, protein_g=2.7, carbs_g=28, fat_g=0.3),
            )
        ],
        totals=Nutrition(kcal=130, protein_g=2.7, carbs_g=28, fat_g=0.3),
    )
    html = render_result_fragment(result)
    assert "Energy" in html
    assert "130" in html


# --- 7. Additional CLI & Web Views Tests ---

def test_cli_history(monkeypatch, tmp_path, capsys):
    import asyncio
    monkeypatch.setenv("STORAGE_BACKEND", "jsonl")
    history_file = tmp_path / "history.jsonl"
    monkeypatch.setenv("HISTORY_JSONL_PATH", str(history_file))
    
    from src.storage.repository import JsonlHistoryRepository
    from src.models import AnalysisResult, HistoryRecord
    from ai import Nutrition
    import datetime
    
    repo = JsonlHistoryRepository(history_file)
    asyncio.run(repo.save(HistoryRecord(
        id="1",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        image_path="dummy.png",
        status="ok",
        ingredients=[],
        rows=[],
        totals=Nutrition(),
        errors=[]
    )))
    
    exit_code = main(["history", "--limit", "2"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data) == 1
    assert data[0]["id"] == "1"


def test_cli_unknown_meal(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("OFFLINE_MODE", "True")
    monkeypatch.setenv("STORAGE_BACKEND", "none")
    
    img = tmp_path / "unknown_meal_test.png"
    img.write_bytes(PNG_BYTES)
    
    exit_code = main(["analyze", str(img), "--offline", "--no-storage"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Meal not recognized in image" in captured.out


def test_provider_error_messages():
    from src.web.views import provider_error_message
    from ai.providers.base import ProviderError
    
    assert "rate limit" in provider_error_message(ProviderError("Rate limit reached 429")).lower()
    assert "timed out" in provider_error_message(ProviderError("Connection timed out")).lower()
    assert "usda" in provider_error_message(ProviderError("USDA service error")).lower()
    assert "failed" in provider_error_message(ProviderError("Unknown backend error")).lower()


def test_render_result_fragment_unknown_meal():
    from src.web.views import render_result_fragment
    from src.models import AnalysisResult
    
    result = AnalysisResult(
        status="unknown_meal",
        image_path="dummy.png",
        ingredients=[],
        rows=[],
        totals=Nutrition(),
        errors=["Meal not recognized"]
    )
    html = render_result_fragment(result)
    assert "Meal not recognized in the image" in html


def test_main_module():
    import runpy
    import sys
    from unittest.mock import patch
    with patch.object(sys, "argv", ["foodanalyzer", "--help"]):
        with pytest.raises(SystemExit):
            runpy.run_module("src.__main__", run_name="__main__")
