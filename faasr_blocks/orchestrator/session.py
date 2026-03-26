"""In-memory conversation and orchestration state for the agent (Phase 4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from faasr_blocks.models.contract import Contract

OrchestrationPhase = Literal["idle", "awaiting_clarification", "awaiting_approval"]


@dataclass
class OrchestratorSession:
    """
    Conversation history plus multi-turn orchestration state.

    Phases:
    - idle: next user message starts a new workflow request unless it is an approval/revision
      while contracts are still pending (handled in the command handler).
    - awaiting_clarification: user should answer questions; next message is treated as answers.
    - awaiting_approval: contracts are shown; user approves or requests revision.
    """

    _messages: list[dict[str, Any]] = field(default_factory=list)

    phase: OrchestrationPhase = "idle"
    """High-level orchestration state."""

    original_request: str = ""
    """First natural-language workflow description for this round."""

    clarification_notes: str = ""
    """Accumulated user answers to clarifying questions."""

    clarification_round: int = 0
    """How many clarification rounds have been sent (used to cap re-asking)."""

    pending_contracts: list[Contract] | None = None
    """Draft contracts awaiting user approval."""

    pending_nl_summaries: list[str] | None = None
    """Parallel natural-language summaries for pending contracts."""

    pending_workflow_edges: list[tuple[str, str]] | None = None
    """Suggested DAG edges (from_block, to_block) for the summary."""

    def add_user_message(self, content: str) -> None:
        """Append a user turn."""
        self._messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """Append an assistant turn."""
        self._messages.append({"role": "assistant", "content": content})

    def clear(self) -> None:
        """Remove all messages and reset orchestration state."""
        self._messages.clear()
        self.phase = "idle"
        self.original_request = ""
        self.clarification_notes = ""
        self.clarification_round = 0
        self.pending_contracts = None
        self.pending_nl_summaries = None
        self.pending_workflow_edges = None

    def get_history(self) -> list[dict[str, Any]]:
        """
        Return a shallow copy of the message list.

        Returns:
            List of dicts with keys ``role`` and ``content``.
        """
        return list(self._messages)

    def reset_pending(self) -> None:
        """Clear pending contracts and return phase to idle after a completed round."""
        self.phase = "idle"
        self.pending_contracts = None
        self.pending_nl_summaries = None
        self.pending_workflow_edges = None
        self.clarification_notes = ""
        self.clarification_round = 0
        self.original_request = ""
