"""LLM-backed generation of pytest files and fixtures for a block."""

from __future__ import annotations

import json

from faasr_blocks.builder.artifact_parse import parse_marked_files
from faasr_blocks.builder.block_context import BlockContext
from faasr_blocks.builder.llm import LLMClient
from faasr_blocks.builder.reference_snippets import default_snippets, example_block_test

SYSTEM_PROMPT = """You are an expert Python test author for FaaSr workflow function blocks.

Requirements:
- Use pytest.
- Import and use `faasr_test_environment` from `faasr_blocks.testing.harness`.
- Patch FaaSr stubs where they are *used* in the block module: pass the block's import path as
  `module_qualname`, e.g. `blocks.<BlockName>.src.<module_name>` matching how tests will import the module.
- Prefer importing the block as: `import blocks.<BlockName>.src.<module_name> as mod` (repo root on PYTHONPATH).
- Put static fixture files under `tests/fixtures/` and load them in tests.
- Cover the contract: happy path, required secrets (mock `env.secret.with_secret(...)`), and S3 uploads
  (assert `env.put_file.uploaded_files` when applicable).
- For `return_type` bool contracts, assert `env.return_.return_value` after calling the function.
- Mock external HTTP (e.g. `requests.get`) when the block calls the network.
- Align the mock with how the implementation reads the body: if code uses `response.json()`, set
  `mock_resp.json.return_value = payload`. If code uses `response.text` / writes `response.text` to a file,
  set `mock_resp.text = json.dumps(payload)` (a real `str`). If you only set `json.return_value` but the
  implementation uses `.text`, tests fail with TypeError (MagicMock is not str).

S3 input data / faasr_get_file and fixtures:
- The test harness mocks `faasr_get_file` by copying files from `tests/fixtures/`. The mock looks up a path
  using `remote_file` (and optional `remote_folder`). For a flat remote file `foo.csv`, it expects
  `tests/fixtures/foo.csv` unless nested under `remote_folder/fixtures/...`.
- Read `preconditions` and `methodology` together. If they require a specific file (CSV, JSON, etc.) with
  named columns or fields, you MUST create that file under `tests/fixtures/` with the exact basename the
  contract implies (or that function arguments will pass to `faasr_get_file`). Populate minimal plausible
  rows so pandas/json parsing and any \"at least N days/rows\" requirements in preconditions are satisfied.
- Happy-path tests: ensure every `faasr_get_file` call in the implementation can resolve to a fixture you
  emitted. Do not emit unrelated fixtures (e.g. only JSON) when preconditions clearly require a CSV with
  matching columns; the implementation is likely to use that filename.
- Negative tests may omit fixtures or use wrong paths to assert `FileNotFoundError` or contract errors only
  when the contract or test intent clearly covers missing data.

- Output ONLY marked files as specified in the user message — no extra commentary outside those sections.
"""

USER_PROMPT_TEMPLATE = """
Block name: {block_name}
Primary module file (create under src/): {function_name}.py
Tests import path for faasr_test_environment second argument:
  blocks.{block_name}.src.{function_name}

Contract (JSON):
{contract_json}
{extra}

Reference: Python API (excerpt)
---
{snippets}
---

Example existing block test (pattern only; adapt to this contract):
```python
{example}
```

Output format (required). Emit one or more sections exactly like this:

### FILE: tests/test_{function_name}.py
```python
# full test module
```

### FILE: tests/fixtures/some_file.json
```json
{{}}
```
(or CSV, text, PNG test inputs as required by preconditions — match filenames to what S3 inputs describe)

Use at least:
- tests/test_{function_name}.py
- Every S3 input file described in contract preconditions (correct basename under tests/fixtures/), plus any
  extra fixtures for HTTP mocks or secrets

Do not emit src/ implementation here — tests only.
"""


def get_user_prompt(
    block_name: str,
    function_name: str,
    contract_json: str,
    extra: str,
    snippets: str,
    example: str,
) -> str:
    return USER_PROMPT_TEMPLATE.format(
        block_name=block_name,
        function_name=function_name,
        contract_json=contract_json,
        extra=extra,
        snippets=snippets,
        example=example,
    ).strip()


class TestGenerator:
    """
    Generate pytest test files from a contract using an LLM.

    The generator creates comprehensive test coverage including:
    - Happy path tests with all contract arguments
    - Secret access tests (mock env.secret.with_secret)
    - S3 output validation (assert env.put_file.uploaded_files)
    - Conditional return tests for bool return_type blocks
    - Fixture files for test data
    """

    def __init__(self, llm: LLMClient, context: BlockContext) -> None:
        """
        Initialize the test generator.

        Args:
            llm: LLM client for generating test code.
            context: Block paths, contract, and repo layout.
        """
        self._llm = llm
        self._context = context

    def generate(self, extra_instructions: str = "") -> None:
        """
        Generate pytest tests for the block and write to block_path/tests/.

        Creates tests/test_<function_name>.py and any necessary fixture files under
        tests/fixtures/. The LLM prompt includes the contract, reference documentation,
        and example tests for pattern matching.

        Args:
            extra_instructions: Optional additional requirements (e.g., from retry failures).
        """
        # Extract context values
        contract = self._context.contract
        block_path = self._context.block_path
        repo_root = self._context.repo_root
        function_name = self._context.function_name
        block_name = self._context.block_name

        # Prepare the prompt
        snippets = default_snippets(repo_root)
        example = example_block_test(repo_root)
        contract_json = json.dumps(contract.model_dump(mode="json"), indent=2)
        extra = (
            f"\n\nAdditional instructions:\n{extra_instructions}\n" if extra_instructions else ""
        )
        user = get_user_prompt(
            block_name, function_name, contract_json, extra, snippets["py_api"], example
        )

        # Call the LLM to generate the test files
        raw = self._llm.complete(SYSTEM_PROMPT, user)

        # Parse the LLM output
        try:
            files = parse_marked_files(raw)
        except ValueError:
            raise ValueError(f"Failed to parse LLM output: {raw[:500]!r}")

        # Write the test files to the block directory
        for rel, content in files.items():
            out = block_path / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
