"""OpenAI-compatible chat client for block builder prompts."""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

import httpx


@runtime_checkable
class LLMClient(Protocol):
    """Minimal interface for testability (inject mocks)."""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return assistant text (non-streaming)."""
        ...


class OpenAIChatLLM:
    """
    Chat Completions API (OpenAI-compatible).

    Environment:
        OPENAI_API_KEY: required
        OPENAI_BASE_URL: default ``https://api.openai.com/v1``
        OPENAI_MODEL: default ``gpt-4o-mini``
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float = 120.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base = (
            base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        ).rstrip("/")
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self._timeout = timeout_s

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self._api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Export it or pass api_key= to OpenAIChatLLM."
            )
        url = f"{self._base}/chat/completions"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self._timeout) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected chat completions response: {data!r}") from e


class StaticMockLLM:
    """Return canned responses in order (for unit tests)."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._i = 0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if self._i >= len(self._responses):
            raise RuntimeError("StaticMockLLM: no more canned responses")
        out = self._responses[self._i]
        self._i += 1
        return out
