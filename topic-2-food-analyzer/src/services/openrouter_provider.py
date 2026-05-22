"""OpenRouter VLM adapter using the OpenAI SDK without touching ai/."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from types import ModuleType
from typing import Any

from ai.providers.base import ProviderError, VLMProvider

from src.config import Settings
from src.validation import media_type_for_path


class OpenRouterVLM(VLMProvider):
    """Vision-language provider for OpenRouter's OpenAI-compatible API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        reasoning_enabled: bool = True,
        logger: logging.Logger | None = None,
    ) -> None:
        if not api_key:
            raise ProviderError("OPENROUTER_API_KEY is not set.")
        try:
            from openai import OpenAI
            import openai
        except ImportError as exc:
            raise ProviderError("Install `openai` to use OpenRouter.") from exc
        self.model = model
        self.reasoning_enabled = reasoning_enabled
        self._logger = logger or logging.getLogger(__name__)
        self._provider_errors = _openai_error_types(openai)
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    @classmethod
    def from_settings(cls, settings: Settings) -> "OpenRouterVLM":
        return cls(
            api_key=settings.openrouter_api_key,
            model=settings.llm_model,
            base_url=settings.openrouter_base_url,
            reasoning_enabled=settings.openrouter_reasoning_enabled,
        )

    def describe(self, image_path: str, prompt: str, *, json_schema: dict | None = None) -> str:
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(image_path)
        try:
            data_url = self._data_url(path)
        except OSError as exc:
            raise ProviderError(f"Could not read image for OpenRouter: {exc}") from exc
        full_prompt = prompt
        if json_schema is not None:
            full_prompt = (
                prompt
                + "\n\nReturn ONLY valid JSON matching this schema, with no markdown:\n"
                + json.dumps(json_schema, indent=2)
            )
        body: dict[str, object] = {}
        if self.reasoning_enabled:
            body["reasoning"] = {"enabled": True}
        request_payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt},
                        {"type": "image_url", "image_url": {"url": "[base64-image-redacted]"}},
                    ],
                }
            ],
            "extra_body": body or None,
        }
        self._logger.debug("openrouter request payload=%s", request_payload)
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": full_prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                extra_body=body or None,
            )
        except self._provider_errors as exc:
            raise ProviderError(f"OpenRouter call failed: {exc}") from exc
        content = (response.choices[0].message.content or "").strip()
        self._logger.debug("openrouter response payload=%s", content)
        return content

    @staticmethod
    def _data_url(path: Path) -> str:
        media_type = media_type_for_path(path)
        encoded = base64.standard_b64encode(path.read_bytes()).decode("ascii")
        return f"data:{media_type};base64,{encoded}"


def openrouter_reasoning_roundtrip_prompt() -> str:
    """Return a ready-to-run snippet for preserving reasoning_details."""

    return (
        "Use the OpenAI SDK with base_url=https://openrouter.ai/api/v1, "
        "pass extra_body={'reasoning': {'enabled': True}}, and preserve "
        "response.choices[0].message.reasoning_details unchanged in the next "
        "messages list when continuing a reasoning conversation."
    )


def _openai_error_types(openai_module: ModuleType | Any) -> tuple[type[BaseException], ...]:
    names = (
        "APIError",
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "BadRequestError",
        "AuthenticationError",
        "PermissionDeniedError",
    )
    classes: list[type[BaseException]] = []
    for name in names:
        candidate = getattr(openai_module, name, None)
        if isinstance(candidate, type) and issubclass(candidate, BaseException):
            classes.append(candidate)
    return tuple(classes) or (RuntimeError,)