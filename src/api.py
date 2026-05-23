"""FastAPI app for Topic 2 HTTP analysis."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from ai.providers.base import ProviderError
from src.config import Settings
from src.core.analyzer import MealAnalyzer
from src.models import AnalyzeResponse
from src.validation import ImageValidationError, validate_image_path
from src.web.views import (
    STATIC_DIR,
    provider_error_message,
    render_analyze_page,
    render_error_fragment,
    render_index_page,
    render_result_fragment,
    save_upload_bytes,
    settings_with_offline,
)


app = FastAPI(title="AI Food Analyzer", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/ui", status_code=307)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "logo.svg", media_type="image/svg+xml")


@app.get("/ui", response_class=HTMLResponse)
async def ui() -> HTMLResponse:
    return HTMLResponse(render_index_page())


@app.get("/ui/analyze-page", response_class=HTMLResponse)
async def analyze_page() -> HTMLResponse:
    return HTMLResponse(render_analyze_page())


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...), offline: bool = False) -> AnalyzeResponse:
    settings = Settings.from_env()
    if offline:
        settings = _replace_settings(settings, offline_mode=True)
    suffix = Path(file.filename or "").suffix.lower()
    stem = Path(file.filename or "upload").stem or "upload"
    safe_stem = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in stem)
    target_dir = settings.upload_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{safe_stem}_{uuid4()}{suffix}"
    content = await file.read()
    if len(content) > settings.max_image_size_bytes:
        raise HTTPException(status_code=413, detail="image exceeds configured size limit")
    try:
        target.write_bytes(content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"could not store uploaded image: {exc}") from exc
    try:
        validate_image_path(target, max_size_bytes=settings.max_image_size_bytes)
        result = await MealAnalyzer(settings).analyze(str(target))
    except ImageValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=provider_error_message(exc)) from exc
    return AnalyzeResponse(result=result)


@app.post("/ui/analyze", response_class=HTMLResponse)
async def analyze_ui(
    file: UploadFile = File(...),
    offline: bool = Form(False),
    persist: bool = Form(False),
) -> HTMLResponse:
    settings = settings_with_offline(Settings.from_env(), offline)
    content = await file.read()
    if len(content) > settings.max_image_size_bytes:
        return HTMLResponse(
            render_error_fragment("image exceeds configured size limit"),
        )
    try:
        target = save_upload_bytes(file.filename or "upload.png", content, settings.upload_dir)
        validate_image_path(target, max_size_bytes=settings.max_image_size_bytes)
        result = await MealAnalyzer(settings).analyze(str(target), persist=persist)
    except ImageValidationError as exc:
        return HTMLResponse(render_error_fragment(str(exc)))
    except OSError as exc:
        return HTMLResponse(render_error_fragment(f"could not store uploaded image: {exc}"))
    except ProviderError as exc:
        return HTMLResponse(render_error_fragment(provider_error_message(exc)))
    return HTMLResponse(render_result_fragment(result))


def _replace_settings(settings: Settings, **changes: object) -> Settings:
    data = settings.__dict__.copy()
    data.update(changes)
    return Settings(**data)
