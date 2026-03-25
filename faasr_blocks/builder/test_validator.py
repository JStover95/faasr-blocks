"""LLM-backed check that tests cover the contract."""

from __future__ import annotations

import json
import re
from pathlib import Path

from faasr_blocks.builder.llm import LLMClient
from faasr_blocks.builder.models import ValidationResult
from faasr_blocks.models.contract import Contract

SYSTEM_PROMPT = """You validate whether a pytest file adequately covers a FaaSr block contract.

Reply with a single JSON object only, no markdown fences, no commentary:
{"ok": true}
or
{"ok": false, "gaps": ["short bullet", "..."]}

Adequate means: exercises the entrypoint function, covers required secrets if any, checks S3 outputs
via mocked faasr_put_file when applicable, and for bool return contracts checks faasr_return behavior.
"""


class ContractTestCoverageValidator:
    """
    Validate that a pytest file adequately covers a contract's requirements.

    Uses an LLM to analyze the test file and identify gaps in coverage such as:
    - Missing tests for required secrets
    - No assertions on S3 outputs (faasr_put_file)
    - Missing conditional return tests for bool return_type blocks
    - Uncovered function arguments or edge cases
    """

    def __init__(self, llm: LLMClient) -> None:
        """
        Initialize the validator.

        Args:
            llm: LLM client for analyzing test coverage.
        """
        self._llm = llm

    def validate(self, contract: Contract, test_file: Path) -> ValidationResult:
        """
        Check if test_file adequately covers the contract.

        Sends the contract and test source to the LLM, which returns a JSON response
        indicating whether coverage is adequate and listing any gaps.

        Args:
            contract: Contract specification with expected coverage.
            test_file: Path to the generated test file to validate.

        Returns:
            ValidationResult with ok=True if adequate, or ok=False with gap descriptions.
        """
        if not test_file.is_file():
            return ValidationResult.failure([f"Test file not found: {test_file}"])
        test_src = test_file.read_text(encoding="utf-8")
        contract_json = json.dumps(contract.model_dump(mode="json"), indent=2)
        user = f"""
Contract JSON:
{contract_json}

Test file path: {test_file.name}
---
{test_src}
---
""".strip()
        raw = self._llm.complete(SYSTEM_PROMPT, user).strip()
        raw = _strip_json_fence(raw)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return ValidationResult.failure(
                [f"Test-contract validator returned non-JSON: {raw[:500]!r}"]
            )
        ok = bool(data.get("ok"))
        if ok:
            return ValidationResult.success()
        gaps = data.get("gaps")
        if isinstance(gaps, list):
            errs = [str(g) for g in gaps]
        else:
            errs = [str(data.get("message", "ok=false without gaps"))]
        return ValidationResult.failure(errs)


def _strip_json_fence(text: str) -> str:
    """
    Remove markdown json fence from LLM response if present.

    Args:
        text: LLM response text, possibly wrapped in ```json ... ```.

    Returns:
        Inner JSON text with fences removed, or original text if no fences found.
    """
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text
