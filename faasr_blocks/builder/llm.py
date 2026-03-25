"""OpenAI-compatible chat client for block builder prompts.

This module provides an LLMClient protocol and implementations for calling chat completion APIs
to generate tests and source code. The protocol allows for dependency injection and mock testing.
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

import httpx


@runtime_checkable
class LLMClient(Protocol):
    """
    Minimal interface for LLM chat completions (dependency injection for testing).

    Implementations should handle API authentication, rate limiting, timeouts, and error handling.
    """

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Send system and user messages to the LLM and return the assistant's response.

        Args:
            system_prompt: System message defining the assistant's role and rules.
            user_prompt: User message with the specific request/task.

        Returns:
            The assistant's response text (non-streaming).

        Raises:
            RuntimeError: If the API call fails or credentials are missing.
        """
        ...


class OpenAIChatLLM:
    """
    Chat Completions API client for OpenAI-compatible endpoints.

    Uses httpx to call the /chat/completions endpoint. Supports OpenAI and compatible providers.

    Environment variables:
        OPENAI_API_KEY: Required. API authentication key.
        OPENAI_BASE_URL: Optional. API base URL (default: https://api.openai.com/v1).
        OPENAI_MODEL: Optional. Model name (default: gpt-4o-mini).

    Example:
        >>> llm = OpenAIChatLLM()
        >>> response = llm.complete("You are helpful.", "What is 2+2?")
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float = 120.0,
    ) -> None:
        """
        Initialize the chat client.

        Args:
            api_key: API key (defaults to OPENAI_API_KEY env var).
            base_url: API base URL (defaults to OPENAI_BASE_URL or https://api.openai.com/v1).
            model: Model name (defaults to OPENAI_MODEL or gpt-4o-mini).
            timeout_s: Request timeout in seconds.
        """
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
    """
    Mock LLM client that returns pre-configured responses in sequence.

    Used for unit testing LLM-dependent components without making real API calls.
    Each call to complete() returns the next response in the list.
    """

    def __init__(self, responses: list[str]) -> None:
        """
        Initialize with a list of canned responses.

        Args:
            responses: List of response strings to return in order.
        """
        self._responses = list(responses)
        self._i = 0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Return the next canned response.

        Args:
            system_prompt: Ignored.
            user_prompt: Ignored.

        Returns:
            The next response from the responses list.

        Raises:
            RuntimeError: If all canned responses have been exhausted.
        """
        if self._i >= len(self._responses):
            raise RuntimeError("StaticMockLLM: no more canned responses")
        out = self._responses[self._i]
        self._i += 1
        return out
