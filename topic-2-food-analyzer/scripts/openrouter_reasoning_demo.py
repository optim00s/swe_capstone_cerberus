"""OpenRouter reasoning continuation example using the OpenAI SDK."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI


MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"


def main() -> int:
    client = OpenAI(
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", MODEL),
        messages=[{"role": "user", "content": "How many r's are in the word 'strawberry'?"}],
        extra_body={"reasoning": {"enabled": True}},
    )
    assistant = response.choices[0].message
    messages = [
        {"role": "user", "content": "How many r's are in the word 'strawberry'?"},
        {
            "role": "assistant",
            "content": assistant.content,
            "reasoning_details": assistant.reasoning_details,
        },
        {"role": "user", "content": "Are you sure? Think carefully."},
    ]
    second = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", MODEL),
        messages=messages,
        extra_body={"reasoning": {"enabled": True}},
    )
    print(second.choices[0].message.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
