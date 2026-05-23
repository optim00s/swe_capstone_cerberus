from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from ai.providers.base import ProviderError


def test_openrouter_vlm_success(monkeypatch, tmp_path):
    mock_openai = MagicMock()
    mock_client = MagicMock()
    mock_openai.OpenAI.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"meal_recognized": true}'
    mock_client.chat.completions.create.return_value = mock_response

    monkeypatch.setitem(sys.modules, "openai", mock_openai)

    from src.services.openrouter_provider import OpenRouterVLM

    vlm = OpenRouterVLM(api_key="fake-key", model="fake-model")

    img = tmp_path / "meal_rice.png"
    img.write_bytes(b"some image bytes")

    res = vlm.describe(str(img), "identify ingredients", json_schema={"type": "object"})

    assert res == '{"meal_recognized": true}'
    mock_client.chat.completions.create.assert_called_once()


def test_openrouter_vlm_missing_key():
    from src.services.openrouter_provider import OpenRouterVLM

    with pytest.raises(ProviderError) as exc:
        OpenRouterVLM(api_key="", model="fake-model")

    assert "API_KEY" in str(exc.value)


def test_openrouter_vlm_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)

    from src.services.openrouter_provider import OpenRouterVLM

    with pytest.raises(ProviderError) as exc:
        OpenRouterVLM(api_key="fake-key", model="fake-model")

    assert "Install `openai`" in str(exc.value)
