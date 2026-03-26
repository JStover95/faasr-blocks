"""Query handlers for the orchestrator (Phase 4)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from faasr_blocks.builder.llm import LLMClient
from faasr_blocks.builder.models import BuildResult
from faasr_blocks.discovery.embedding import EmbeddingClient, EmbeddingGenerator
from faasr_blocks.discovery.storage import EmbeddingStore
from faasr_blocks.models.contract import Contract
from faasr_blocks.orchestrator.builder_dispatch import BuilderDispatcher
from faasr_blocks.orchestrator.contract_agent import ContractGenerationAgent
from faasr_blocks.orchestrator.discovery_handler import DiscoveryHandler
from faasr_blocks.orchestrator.session import OrchestratorSession
from faasr_blocks.orchestrator.summary import format_workflow_summary


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


def _is_approval(text: str) -> bool:
    t = text.strip().lower()
    if not t:
        return False
    return t in {
        "yes",
        "y",
        "approve",
        "approved",
        "ok",
        "okay",
        "proceed",
        "go",
        "build",
        "confirm",
        "confirmed",
    }


def _history_as_str_list(session: OrchestratorSession) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in session.get_history():
        role = str(m.get("role", ""))
        content = str(m.get("content", ""))
        out.append({"role": role, "content": content})
    return out


def _format_draft_for_user(
    contracts: list[Contract],
    nl_summaries: list[str],
    edges: list[tuple[str, str]],
) -> str:
    lines: list[str] = [
        "## Draft contracts",
        "",
        "Review the steps below. Reply **approve** (or **yes** / **ok**) to search for reusable "
        "blocks, build any missing ones, and print a summary. Or describe what to change.",
        "",
    ]
    for i, c in enumerate(contracts):
        summary = nl_summaries[i] if i < len(nl_summaries) else c.block_name
        args_desc = ", ".join(f"{n}: {a.type}" for n, a in c.function.arguments.items()) or "(none)"
        lines.append(f"### {i + 1}. {c.block_name}")
        lines.append("")
        lines.append(f"- **Summary:** {summary}")
        lines.append(
            f"- **Function:** `{c.function.name}({args_desc}) -> {c.function.return_type}`",
        )
        lines.append(f"- **Role:** {c.metadata.role} / **Data:** {c.metadata.data_type}")
        if c.required_secrets:
            lines.append(f"- **Secrets:** {', '.join(c.required_secrets)}")
        lines.append("")

    if edges:
        lines.append("### Suggested order")
        lines.append("")
        for a, b in edges:
            lines.append(f"- `{a}` → `{b}`")
        lines.append("")

    return "\n".join(lines)


class OrchestratorCommandHandler:
    """
    Full Phase 4 pipeline: contract generation, optional clarification, approval, discovery, build.
    """

    def __init__(
        self,
        llm: LLMClient,
        embedding_client: EmbeddingClient,
        embedding_store: EmbeddingStore,
        repo_root: Path,
        schema_path: Path,
        *,
        discovery_top_n: int = 5,
        max_source_iterations: int = 3,
    ) -> None:
        self._llm = llm
        self._embedding_store = embedding_store
        self._repo_root = repo_root
        self._schema_path = schema_path
        self._discovery_top_n = discovery_top_n
        self._contract_agent = ContractGenerationAgent(llm, schema_path=schema_path)
        self._discovery = DiscoveryHandler(
            embedding_client,
            embedding_store,
            llm,
            repo_root / "blocks",
        )
        self._embedding_generator = EmbeddingGenerator(embedding_client)
        self._builder = BuilderDispatcher(
            llm,
            self._embedding_generator,
            embedding_store,
            repo_root,
            schema_path,
            max_source_iterations=max_source_iterations,
        )

    def close(self) -> None:
        """Release discovery search engine resources (sqlite-vec)."""
        self._discovery.close()

    def _run_discovery_and_build(
        self,
        session: OrchestratorSession,
        proposed: list[Contract],
        edges: list[tuple[str, str]],
    ) -> str:
        reused: list[tuple[Contract, str]] = []
        built: list[tuple[Contract, BuildResult]] = []
        embedding_notes: list[str] = []

        for c in proposed:
            candidates = self._discovery.find_reusable_blocks(c, top_n=self._discovery_top_n)
            chosen = None
            for cand in candidates:
                if cand.reuse_as_is:
                    if chosen is None or cand.similarity > chosen.similarity:
                        chosen = cand
            if chosen is not None:
                reused.append((chosen.contract, chosen.reasoning))
                continue

            dispatch = self._builder.build_block(c)
            built.append((dispatch.contract, dispatch.build_result))
            if (
                dispatch.build_result.success
                and not dispatch.embedding_uploaded
                and dispatch.embedding_error
            ):
                embedding_notes.append(
                    f"{dispatch.contract.block_name}: embedding not uploaded ({dispatch.embedding_error})",
                )

        summary = format_workflow_summary(
            user_request=session.original_request,
            reused_blocks=reused,
            new_blocks=built,
            workflow_dag=edges,
            blocks_root_display="blocks/",
        )
        if embedding_notes:
            summary += (
                "\n### Embedding notes\n\n" + "\n".join(f"- {n}" for n in embedding_notes) + "\n"
            )

        session.reset_pending()
        session.add_assistant_message(summary)
        return summary

    def _handle_awaiting_clarification(self, query: str, session: OrchestratorSession) -> str:
        if session.clarification_notes:
            session.clarification_notes += "\n\n" + query.strip()
        else:
            session.clarification_notes = query.strip()

        result = self._contract_agent.generate(
            mode="after_clarify",
            user_line=query,
            history=_history_as_str_list(session),
            original_request=session.original_request,
            clarification_answers=session.clarification_notes,
        )

        if result.kind == "error":
            msg = f"## Contract generation error\n\n{result.error_message}\n"
            session.add_assistant_message(msg)
            return msg

        if result.kind == "clarify" and session.clarification_round < 1:
            session.clarification_round += 1
            qs = (
                "\n".join(f"{i + 1}. {q}" for i, q in enumerate(result.questions))
                or "(no questions)"
            )
            msg = f"## A few more questions\n\n{qs}\n\nPlease answer in your next message."
            session.add_assistant_message(msg)
            return msg

        if result.kind == "clarify":
            msg = (
                "## Could not finalize contracts\n\n"
                "Please simplify your request or add concrete details (inputs, outputs, APIs, formats). "
                "You can start over with a new description."
            )
            session.phase = "idle"
            session.clarification_round = 0
            session.clarification_notes = ""
            session.add_assistant_message(msg)
            return msg

        session.pending_contracts = result.contracts
        session.pending_nl_summaries = result.nl_summaries
        session.pending_workflow_edges = result.workflow_edges
        session.phase = "awaiting_approval"
        session.clarification_round = 0
        session.clarification_notes = ""
        body = _format_draft_for_user(
            result.contracts,
            result.nl_summaries,
            result.workflow_edges,
        )
        session.add_assistant_message(body)
        return body

    def _handle_awaiting_approval(self, query: str, session: OrchestratorSession) -> str:
        pending = session.pending_contracts or []
        edges = session.pending_workflow_edges or []

        if _is_approval(query):
            if not pending:
                msg = "## Nothing to build\n\nNo pending contracts. Describe a workflow to begin.\n"
                session.phase = "idle"
                session.add_assistant_message(msg)
                return msg
            session.phase = "idle"
            return self._run_discovery_and_build(session, pending, edges)

        result = self._contract_agent.generate(
            mode="revise",
            user_line=query,
            history=_history_as_str_list(session),
            original_request=session.original_request,
            previous_contracts=pending,
        )

        if result.kind == "error":
            msg = f"## Revision error\n\n{result.error_message}\n"
            session.add_assistant_message(msg)
            return msg

        if result.kind == "clarify":
            session.phase = "awaiting_clarification"
            session.clarification_round = 0
            qs = (
                "\n".join(f"{i + 1}. {q}" for i, q in enumerate(result.questions))
                or "(no questions)"
            )
            msg = f"## Clarifications needed\n\n{qs}\n"
            session.add_assistant_message(msg)
            return msg

        session.pending_contracts = result.contracts
        session.pending_nl_summaries = result.nl_summaries
        session.pending_workflow_edges = result.workflow_edges
        body = _format_draft_for_user(
            result.contracts,
            result.nl_summaries,
            result.workflow_edges,
        )
        session.add_assistant_message(body)
        return body

    def _handle_idle(self, query: str, session: OrchestratorSession) -> str:
        session.original_request = query.strip()
        session.clarification_round = 0
        session.clarification_notes = ""

        result = self._contract_agent.generate(
            mode="initial",
            user_line=query,
            history=_history_as_str_list(session),
            original_request=session.original_request,
        )

        if result.kind == "error":
            msg = f"## Contract generation error\n\n{result.error_message}\n"
            session.add_assistant_message(msg)
            return msg

        if result.kind == "clarify":
            session.phase = "awaiting_clarification"
            session.clarification_round = 0
            qs = (
                "\n".join(f"{i + 1}. {q}" for i, q in enumerate(result.questions))
                or "(no questions)"
            )
            msg = f"## Clarifying questions\n\n{qs}\n\nPlease answer in your next message."
            session.add_assistant_message(msg)
            return msg

        session.pending_contracts = result.contracts
        session.pending_nl_summaries = result.nl_summaries
        session.pending_workflow_edges = result.workflow_edges
        session.phase = "awaiting_approval"
        body = _format_draft_for_user(
            result.contracts,
            result.nl_summaries,
            result.workflow_edges,
        )
        session.add_assistant_message(body)
        return body

    def handle(self, query: str, session: OrchestratorSession) -> str:
        if session.phase == "awaiting_clarification":
            return self._handle_awaiting_clarification(query, session)
        if session.phase == "awaiting_approval":
            return self._handle_awaiting_approval(query, session)
        return self._handle_idle(query, session)


class StubHandler:
    """
    Placeholder handler (Phase 4a) for tests or offline demos.

    Prefer :class:`OrchestratorCommandHandler` for the full pipeline.
    """

    def handle(self, query: str, session: OrchestratorSession) -> str:
        lines = [
            "## Stub response (Phase 4a)",
            "",
            f"You asked: **{query.strip()[:200]}{'…' if len(query.strip()) > 200 else ''}**",
            "",
            "### What would happen next",
            "",
            "1. **Block discovery** — Embed this request and search for similar blocks.",
            "2. **Contract proposals** — Draft one contract per workflow step.",
            "3. **Build** — Run the block builder (tests → implementation → pytest).",
            "4. **Summary** — Emit a markdown summary of reused vs newly created blocks.",
            "",
            "_Use OrchestratorCommandHandler for the real agent._",
        ]
        text = "\n".join(lines)
        session.add_assistant_message(text)
        return text
