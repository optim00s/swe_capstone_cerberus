"""Typed application settings loaded from environment variables."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int, *, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    value = default if raw is None or raw.strip() == "" else int(raw)
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _get_float(name: str, default: float, *, minimum: float | None = None) -> float:
    raw = os.getenv(name)
    value = default if raw is None or raw.strip() == "" else float(raw)
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


@dataclass(frozen=True)
class Settings:
    """Runtime settings shared by CLI, API, and tests."""

    llm_provider: str = "openrouter"
    llm_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_reasoning_enabled: bool = False

    nutrition_provider: str = "usda"
    usda_api_key: str = ""

    log_level: str = "INFO"
    database_url: str = "postgresql://postgres:dev@localhost:5432/foodanalyzer"
    storage_backend: str = "jsonl"
    history_jsonl_path: Path = Path("artefacts/history.jsonl")
    upload_dir: Path = Path("runtime/uploads")

    nutrition_cache_backend: str = "memory"
    nutrition_cache_ttl_seconds: int = 86400
    max_image_size_mb: int = 5
    max_parallel_lookups: int = 10
    retry_attempts: int = 3
    retry_base_delay_seconds: float = 0.2
    ai_timeout_seconds: float = 30.0
    rate_limit_tokens: int = 10
    rate_limit_refill_per_second: float = 10.0
    http_port: int = 8000

    offline_mode: bool = False

    @classmethod
    def from_env(cls, *, load_dotenv: bool = True) -> "Settings":
        if load_dotenv:
            _load_dotenv()
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", cls.llm_provider).strip().lower(),
            llm_model=os.getenv("LLM_MODEL", cls.llm_model).strip(),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", cls.openrouter_base_url).strip(),
            openrouter_reasoning_enabled=_get_bool("OPENROUTER_REASONING_ENABLED", cls.openrouter_reasoning_enabled),
            nutrition_provider=os.getenv("NUTRITION_PROVIDER", cls.nutrition_provider).strip().lower(),
            usda_api_key=os.getenv("USDA_API_KEY", ""),
            log_level=os.getenv("LOG_LEVEL", cls.log_level).strip().upper(),
            database_url=os.getenv("DATABASE_URL", cls.database_url).strip(),
            storage_backend=os.getenv("STORAGE_BACKEND", cls.storage_backend).strip().lower(),
            history_jsonl_path=Path(os.getenv("HISTORY_JSONL_PATH", str(cls.history_jsonl_path))),
            upload_dir=Path(os.getenv("UPLOAD_DIR", str(cls.upload_dir))),
            nutrition_cache_backend=os.getenv(
                "NUTRITION_CACHE_BACKEND",
                cls.nutrition_cache_backend,
            ).strip().lower(),
            nutrition_cache_ttl_seconds=_get_int("NUTRITION_CACHE_TTL_SECONDS", 86400, minimum=0),
            max_image_size_mb=_get_int("MAX_IMAGE_SIZE_MB", 5, minimum=1),
            max_parallel_lookups=_get_int("MAX_PARALLEL_LOOKUPS", 10, minimum=1),
            retry_attempts=_get_int("RETRY_ATTEMPTS", 3, minimum=1),
            retry_base_delay_seconds=_get_float("RETRY_BASE_DELAY_SECONDS", 0.2, minimum=0.0),
            ai_timeout_seconds=_get_float("AI_TIMEOUT_SECONDS", 30.0, minimum=0.1),
            rate_limit_tokens=_get_int("RATE_LIMIT_TOKENS", 10, minimum=1),
            rate_limit_refill_per_second=_get_float("RATE_LIMIT_REFILL_PER_SECOND", 10.0, minimum=0.001),
            http_port=_get_int("HTTP_PORT", 8000, minimum=1),
            offline_mode=_get_bool("OFFLINE_MODE", False),
        )

    @property
    def max_image_size_bytes(self) -> int:
        return self.max_image_size_mb * 1024 * 1024

    @property
    def uses_openrouter(self) -> bool:
        return self.llm_provider == "openrouter"
