"""LLM-driven contract generation for the orchestrator (Phase 4)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from faasr_blocks.builder.llm import LLMClient
from faasr_blocks.models.contract import Contract


def _extract_json_value(text: str) -> object:
    """Parse JSON object or array from model output (strip markdown fences)."""
    s = text.strip()
    fence = re.search(r"```(?:json)?\s*([\[\{].*[\]\}])\s*```", s, re.DOTALL)
    if fence:
        s = fence.group(1).strip()
    else:
        if s.startswith("{") or s.startswith("["):
            pass
        else:
            start_obj = s.find("{")
            start_arr = s.find("[")
            if start_obj == -1:
                start = start_arr
            elif start_arr == -1:
                start = start_obj
            else:
                start = min(start_obj, start_arr)
            end_obj = s.rfind("}")
            end_arr = s.rfind("]")
            end = max(end_obj, end_arr)
            if start != -1 and end != -1 and end > start:
                s = s[start : end + 1]
    return json.loads(s)


def _format_history(history: list[dict[str, str]], max_turns: int = 20) -> str:
    """Turn recent chat messages into a plain-text block for the prompt."""
    tail = history[-max_turns:] if len(history) > max_turns else history
    lines: list[str] = []
    for m in tail:
        role = m.get("role", "")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines) if lines else "(no prior turns)"


@dataclass
class ContractGenerationResult:
    """Outcome of one contract-generation LLM call."""

    kind: Literal["clarify", "contracts", "error"]
    questions: list[str]
    contracts: list[Contract]
    nl_summaries: list[str]
    workflow_edges: list[tuple[str, str]]
    raw_assistant: str
    error_message: str


class ContractGenerationAgent:
    """
    Produces FaaSr block contracts from natural language, or asks clarifying questions.

    The model must return JSON only (see system prompt). Contracts are validated with Pydantic.
    """

    def __init__(self, llm: LLMClient, schema_path: Path | None = None) -> None:
        self._llm = llm
        self._schema_path = schema_path

    def _load_schema_excerpt(self) -> str:
        if self._schema_path and self._schema_path.is_file():
            return self._schema_path.read_text(encoding="utf-8", errors="replace")[:12000]
        return "{}"

    def _system_prompt(self) -> str:
        schema = self._load_schema_excerpt()
        return f"""You are the FaaSr Blocks orchestrator contract planner.

Goal: From the user's workflow description, either ask clarifying questions OR emit concrete block contracts.

Each block is one Python module with a single entrypoint function. Two different naming layers:

1) Contract field function.name — the block's own entrypoint (snake_case), describing what the step does.
   Derive it from block_name: PascalCase -> snake_case (e.g. DownloadGHCNDData -> download_ghcnd_data,
   GetWeatherData -> get_weather_data). This is NOT a FaaSr API name.

2) FaaSr client stubs — used only inside the implementation (import from FaaSr_py.client.py_client_stubs):
   faasr_get_file, faasr_put_file, faasr_delete_file, faasr_log; faasr_secret for required_secrets;
   faasr_return(value: bool) only when function.return_type is \"bool\" (branching).

Never set function.name to a FaaSr stub (faasr_get_file, faasr_put_file, faasr_return, faasr_log, etc.).
For return_type \"None\", the entrypoint returns Python None in the normal sense — do not use faasr_return for that.

Blocks are pure and idempotent. Preconditions/postconditions are happy-path only (PoC). Use PascalCase block_name.

Blocks must be workflow-agnostic: never name a specific upstream block or step in preconditions.
If the block reads artifacts from S3 via faasr_get_file (or similar), preconditions MUST spell out the data
contract so tests can create fixtures: exact filename or stable naming convention, file format (CSV, JSON, etc.),
required fields/columns and types, and any minimum volume (e.g. at least 30 daily rows). Do not rely on vague
phrases like \"data must be downloaded\" without naming the file and schema. If the caller must choose the
input filename, add a function argument (e.g. input_csv) and describe the schema in preconditions; if the
filename is fixed by convention for this block, state that literal name in preconditions.

Contract JSON must conform to this schema (excerpt; honor required fields and types):
{schema}

Respond with JSON only — no markdown fences, no commentary. Two shapes:

1) Clarify (at most 3 short questions; use only if essential information is missing):
{{\"type\":\"clarify\",\"questions\":[\"...\",\"...\"]}}

2) Contracts (one object per workflow step, in execution order):
{{
  \"type\":\"contracts\",
  \"nl_summaries\": [\"plain language summary per contract, same order\"],
  \"workflow_edges\": [[\"BlockA\",\"BlockB\"], ...],
  \"contracts\": [ {{ ...full contract objects... }} ]
}}

Rules:
- version must be semver x.y.z (e.g. 1.0.0).
- function.name must be a custom snake_case entrypoint name (see above), never faasr_*.
- function.arguments: map name -> {{\"type\":\"str|int|float|bool|dict|list|...\",\"description\":\"...\"}}
- s3_outputs: filename, format, description (filename may mention caller-provided names).
- required_secrets: list of secret names or [].
- conditional_return: null unless return_type is bool; then include description, true_condition, false_condition.
- dependencies.python_packages: list of {{\"name\",\"version\"}} with concrete pins like \">=2.31.0\".
- preconditions: for any S3 input the implementation will read, be explicit (filename/pattern, format, schema,
  minimum records). Keep wording independent of workflow order.

If the user already answered clarifications, prefer emitting contracts over asking again unless still impossible."""

    def _parse_response(self, raw: str) -> ContractGenerationResult:
        try:
            data = _extract_json_value(raw)
        except Exception as e:  # noqa: BLE001
            return ContractGenerationResult(
                kind="error",
                questions=[],
                contracts=[],
                nl_summaries=[],
                workflow_edges=[],
                raw_assistant=raw,
                error_message=f"Invalid JSON from model: {e}",
            )

        if not isinstance(data, dict):
            return ContractGenerationResult(
                kind="error",
                questions=[],
                contracts=[],
                nl_summaries=[],
                workflow_edges=[],
                raw_assistant=raw,
                error_message="Top-level JSON must be an object.",
            )

        kind = data.get("type")
        if kind == "clarify":
            qs = data.get("questions") or []
            if not isinstance(qs, list):
                qs = []
            questions = [str(q).strip() for q in qs if str(q).strip()]
            return ContractGenerationResult(
                kind="clarify",
                questions=questions[:5],
                contracts=[],
                nl_summaries=[],
                workflow_edges=[],
                raw_assistant=raw,
                error_message="",
            )

        if kind == "contracts":
            raw_contracts = data.get("contracts") or []
            nl = data.get("nl_summaries") or []
            edges = data.get("workflow_edges") or []

            if not isinstance(raw_contracts, list) or not raw_contracts:
                return ContractGenerationResult(
                    kind="error",
                    questions=[],
                    contracts=[],
                    nl_summaries=[],
                    workflow_edges=[],
                    raw_assistant=raw,
                    error_message="contracts array missing or empty.",
                )

            contracts: list[Contract] = []
            for i, obj in enumerate(raw_contracts):
                if not isinstance(obj, dict):
                    return ContractGenerationResult(
                        kind="error",
                        questions=[],
                        contracts=[],
                        nl_summaries=[],
                        workflow_edges=[],
                        raw_assistant=raw,
                        error_message=f"contracts[{i}] is not an object.",
                    )
                try:
                    contracts.append(Contract.model_validate(obj))
                except Exception as e:  # noqa: BLE001
                    return ContractGenerationResult(
                        kind="error",
                        questions=[],
                        contracts=[],
                        nl_summaries=[],
                        workflow_edges=[],
                        raw_assistant=raw,
                        error_message=f"Contract validation failed for contracts[{i}]: {e}",
                    )

            nl_summaries = [str(x).strip() for x in nl] if isinstance(nl, list) else []
            while len(nl_summaries) < len(contracts):
                nl_summaries.append(contracts[len(nl_summaries)].block_name)

            wf: list[tuple[str, str]] = []
            if isinstance(edges, list):
                for e in edges:
                    if (
                        isinstance(e, (list, tuple))
                        and len(e) == 2
                        and isinstance(e[0], str)
                        and isinstance(e[1], str)
                    ):
                        wf.append((e[0].strip(), e[1].strip()))

            return ContractGenerationResult(
                kind="contracts",
                questions=[],
                contracts=contracts,
                nl_summaries=nl_summaries[: len(contracts)],
                workflow_edges=wf,
                raw_assistant=raw,
                error_message="",
            )

        return ContractGenerationResult(
            kind="error",
            questions=[],
            contracts=[],
            nl_summaries=[],
            workflow_edges=[],
            raw_assistant=raw,
            error_message=f"Unknown type field: {kind!r}",
        )

    def generate(
        self,
        *,
        mode: Literal["initial", "after_clarify", "revise"],
        user_line: str,
        history: list[dict[str, str]],
        original_request: str,
        clarification_answers: str | None = None,
        previous_contracts: list[Contract] | None = None,
    ) -> ContractGenerationResult:
        """
        Run one contract-generation step.

        Args:
            mode: initial user request, follow-up after clarifications, or revision of prior contracts.
            user_line: Latest user message for this step.
            history: Orchestrator chat history (role/content).
            original_request: First user workflow description (for context).
            clarification_answers: Consolidated answers when mode is after_clarify.
            previous_contracts: Prior contracts when mode is revise.

        Returns:
            ContractGenerationResult.
        """
        hist = _format_history(history)
        parts = [
            "### Original workflow request",
            original_request.strip() or "(none)",
            "",
            "### Recent conversation",
            hist,
            "",
        ]
        if mode == "after_clarify" and clarification_answers:
            parts.extend(
                [
                    "### User answers to clarifying questions",
                    clarification_answers.strip(),
                    "",
                ]
            )
        if mode == "revise" and previous_contracts:
            prev = [c.model_dump(mode="json") for c in previous_contracts]
            parts.extend(
                [
                    "### Previous draft contracts (revise per user feedback)",
                    json.dumps(prev, indent=2),
                    "",
                ]
            )

        parts.extend(
            [
                "### Current user instruction",
                user_line.strip(),
                "",
                "Return JSON only as specified in the system prompt.",
            ]
        )
        user_prompt = "\n".join(parts)
        raw = self._llm.complete(self._system_prompt(), user_prompt)
        return self._parse_response(raw)
