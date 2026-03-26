"""LLM-backed generation of pytest files and fixtures for a block."""

from __future__ import annotations

import json

from faasr_blocks.builder.artifact_parse import extract_single_python_module, parse_marked_files
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
- Output ONLY marked files as specified in the user message — no extra commentary outside those sections.
"""


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
        contract = self._context.contract
        block_path = self._context.block_path
        repo_root = self._context.repo_root
        fn = self._context.function_name
        block_name = self._context.block_name
        module_name = fn  # convention: get_weather_data.py
        snippets = default_snippets(repo_root)
        example = example_block_test(repo_root)

        contract_json = json.dumps(contract.model_dump(mode="json"), indent=2)
        extra = (
            f"\n\nAdditional instructions:\n{extra_instructions}\n" if extra_instructions else ""
        )
        user = f"""
Block name: {block_name}
Primary module file (create under src/): {module_name}.py
Tests import path for faasr_test_environment second argument:
  blocks.{block_name}.src.{module_name}

Contract (JSON):
{contract_json}
{extra}

Reference: Python API (excerpt)
---
{snippets["py_api"]}
---

Example existing block test (pattern only; adapt to this contract):
```python
{example}
```

Output format (required). Emit one or more sections exactly like this:

### FILE: tests/test_{fn}.py
```python
# full test module
```

### FILE: tests/fixtures/some_file.json
```json
{{}}
```

Use at least:
- tests/test_{fn}.py
- any fixtures your tests need under tests/fixtures/

Do not emit src/ implementation here — tests only.
""".strip()

        raw = self._llm.complete(SYSTEM_PROMPT, user)
        try:
            files = parse_marked_files(raw)
        except ValueError:
            # Fallback: single test file
            body = extract_single_python_module(raw)
            files = {f"tests/test_{fn}.py": body}

        for rel, content in files.items():
            out = block_path / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
