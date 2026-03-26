"""In-memory conversation state for the orchestrator agent (Phase 4a PoC)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrchestratorSession:
    """
    Manage conversation history for future LLM context.

    Messages are simple role/content dicts suitable for chat APIs.
    """

    _messages: list[dict[str, Any]] = field(default_factory=list)

    def add_user_message(self, content: str) -> None:
        """Append a user turn."""
        self._messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """Append an assistant turn."""
        self._messages.append({"role": "assistant", "content": content})

    def clear(self) -> None:
        """Remove all messages."""
        self._messages.clear()

    def get_history(self) -> list[dict[str, Any]]:
        """
        Return a shallow copy of the message list.

        Returns:
            List of dicts with keys ``role`` and ``content``.
        """
        return list(self._messages)
