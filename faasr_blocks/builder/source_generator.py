"""LLM-backed generation of block implementation under src/."""

from __future__ import annotations

import json
from pathlib import Path

from faasr_blocks.builder.artifact_parse import extract_single_python_module, parse_marked_files
from faasr_blocks.builder.llm import LLMClient
from faasr_blocks.builder.reference_snippets import default_snippets
from faasr_blocks.models.contract import Contract

SYSTEM_PROMPT = """You are an expert Python author for FaaSr serverless functions.

Rules:
- Import FaaSr client stubs from: `from FaaSr_py.client.py_client_stubs import ...`
  Use only: faasr_get_file, faasr_put_file, faasr_delete_file, faasr_log, faasr_secret,
  faasr_return (when contract return_type is bool), faasr_get_folder_list, faasr_rank,
  faasr_get_s3_creds, faasr_invocation_id, faasr_exit as needed by the contract.
- Implement the contract entrypoint function with the exact name and parameter list from the contract.
- For return_type "None", do not call faasr_return.
- For return_type "bool", end the successful path with faasr_return(True/False) as appropriate.
- Keep the block pure/idempotent per contract pre/postconditions.
- Match the tests: implementation must satisfy the provided pytest file behaviors.
- For JSON over HTTP (``requests``): prefer ``payload = response.json()`` then ``json.dump(payload, f, indent=2)``
  so tests can use ``MagicMock`` with ``mock_resp.json.return_value = {...}``. Using ``response.text`` breaks
  such tests because ``mock.text`` defaults to another ``MagicMock``, not a ``str``.

Output format:
Either a single ```python fenced block with the full module, OR marked files:

### FILE: src/<module>.py
```python
...
```
"""


class SourceCodeGenerator:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def generate(
        self,
        contract: Contract,
        block_path: Path,
        repo_root: Path,
        test_source: str,
        extra_instructions: str = "",
    ) -> None:
        fn = contract.function.name
        module_file = f"src/{fn}.py"
        snippets = default_snippets(repo_root)
        contract_json = json.dumps(contract.model_dump(mode="json"), indent=2)

        user = f"""
{extra_instructions}

Contract JSON:
{contract_json}

Reference tutorial example (pattern):
```python
{snippets["compute_sum_py"]}
```

Py API excerpt:
---
{snippets["py_api"]}
---

Current tests (implementation must pass these):
```python
{test_source}
```

Emit the implementation as:

### FILE: {module_file}
```python
# full module
```
""".strip()

        raw = self._llm.complete(SYSTEM_PROMPT, user)
        try:
            files = parse_marked_files(raw)
        except ValueError:
            body = extract_single_python_module(raw)
            files = {module_file: body}

        # Prefer exact module path
        key = module_file
        if key not in files:
            # allow alternate key without src/
            alt = f"{fn}.py"
            if alt in files:
                key = alt
            elif len(files) == 1:
                key = next(iter(files))
            else:
                raise ValueError(f"LLM output missing {module_file!r}; got keys {list(files)!r}")

        content = files[key]
        out = block_path / "src" / f"{fn}.py"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
