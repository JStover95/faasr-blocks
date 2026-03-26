"""Query handlers and stub responses for the orchestrator (Phase 4a PoC)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from faasr_blocks.orchestrator.session import OrchestratorSession


@runtime_checkable
class CommandHandler(Protocol):
    """
    Handle a natural-language workflow request (not slash commands).

    Implementations update ``session`` as appropriate and return assistant text.
    """

    def handle(self, query: str, session: OrchestratorSession) -> str:
        """
        Process user query and return assistant response text.

        Args:
            query: Non-empty user message (slash commands handled elsewhere).
            session: Conversation session to append turns to.

        Returns:
            Assistant message body (markdown/plain text).
        """
        ...


class StubHandler:
    """
    Placeholder handler describing future integration points.

    # TODO: Call discovery.search.SqliteVecSearchEngine here (embed query, top-N blocks).
    # TODO: LLM contract generation from NL input (clarifying questions + contract set).
    # TODO: Launch builder subagent per approved contract (BlockBuilder pipeline).
    # TODO: Format final markdown summary with actual new/reused blocks.
    """

    def handle(self, query: str, session: OrchestratorSession) -> str:
        # Caller (REPL) should append the user turn before invoking handle.
        # Stub: describe what the real agent would do next.
        lines = [
            "## Stub response (Phase 4a)",
            "",
            f"You asked: **{query.strip()[:200]}{'…' if len(query.strip()) > 200 else ''}**",
            "",
            "### What would happen next",
            "",
            "1. **Block discovery** — Embed this request and search for similar blocks "
            "(e.g. `SqliteVecSearchEngine` over embeddings from S3).",
            "2. **Contract proposals** — If gaps remain, draft one contract per workflow step "
            "in natural language for your approval.",
            "3. **Build** — For each approved contract, run the block builder "
            "(tests → implementation → pytest loop).",
            "4. **Summary** — Emit a markdown summary of reused vs newly created blocks.",
            "",
            "### Example contract sketch (illustrative only)",
            "",
            "1. **FetchWeatherData** — Fetch forecast JSON via HTTP; upload with `faasr_put_file`.",
            "2. **ProcessWeatherMetrics** — Read JSON from S3; emit processed metrics JSON.",
            "3. **PlotWeatherSeries** — Read metrics; write PNG via `faasr_put_file`.",
            "",
            "_Reply with more detail to refine requirements, or use `/help` for commands._",
        ]
        text = "\n".join(lines)
        session.add_assistant_message(text)
        return text
