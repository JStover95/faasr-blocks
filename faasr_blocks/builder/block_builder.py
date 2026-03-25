"""Orchestrate test generation, validation, implementation, and pytest."""

from __future__ import annotations

from pathlib import Path

from faasr_blocks.builder.debug_log import debug_enabled, debug_print
from faasr_blocks.builder.llm import LLMClient
from faasr_blocks.builder.models import BuildResult, ValidationResult
from faasr_blocks.builder.source_generator import SourceCodeGenerator
from faasr_blocks.builder.static_validator import StaticValidator
from faasr_blocks.builder.test_generator import TestGenerator
from faasr_blocks.builder.test_runner import TestRunner
from faasr_blocks.builder.test_validator import ContractTestCoverageValidator
from faasr_blocks.models.contract import Contract
from faasr_blocks.validation.block_validator import BlockValidator
from faasr_blocks.validation.contract_validator import ContractValidator


def _pytest_remediation_hints(stdout: str) -> str:
    """
    Detect known pytest failure patterns and return explicit fix instructions for the LLM.

    This heuristic checks for common mock misalignment issues and provides targeted guidance
    to help the source generator fix them on the next iteration.

    Common case: tests mock requests.Response with mock_resp.json.return_value = {...} but
    implementation uses response.text; MagicMock.text is not a str for file.write().

    Args:
        stdout: Pytest stdout output containing failure messages.

    Returns:
        Additional instructions string to append to extra_instructions, or empty string if no hints.
    """
    if not stdout:
        return ""
    if (
        "MagicMock" in stdout
        and "str" in stdout
        and ("write()" in stdout or "must be str" in stdout)
    ):
        return (
            "\n\n[HINT] Pytest shows MagicMock vs str on file write. The tests almost certainly use "
            "``mock_resp.json.return_value = <dict>`` for ``requests.get``. Change the implementation to "
            "parse JSON with ``data = response.json()`` and persist with ``json.dump(data, f, indent=2)`` "
            "(import ``json``). Do not use ``response.text`` for this pattern unless you also change tests "
            "to set ``mock_resp.text`` to a JSON string."
        )
    return ""


def _debug_src_hints(src_file: Path, max_lines: int = 80) -> None:
    """
    Print relevant source code lines when debug mode is enabled.

    Extracts and displays lines containing keywords like 'requests', 'response.', '.text',
    'faasr_', 'open(' to help diagnose mock alignment issues between tests and implementation.

    Only prints when FAASR_BLOCKS_DEBUG=1.

    Args:
        src_file: Path to the source file to inspect.
        max_lines: Maximum number of matching lines to print.
    """
    if not debug_enabled() or not src_file.is_file():
        return
    text = src_file.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    keywords = ("requests", "response.", "json", ".text", "faasr_", "open(", "urllib")
    interesting = [(i, ln) for i, ln in enumerate(lines, start=1) if any(k in ln for k in keywords)]
    debug_print(f"--- src hints {src_file} ({len(lines)} lines) ---")
    if interesting:
        for i, ln in interesting[:max_lines]:
            debug_print(f" L{i:4d}: {ln}")
        if len(interesting) > max_lines:
            debug_print(f" ... ({len(interesting) - max_lines} more matching lines omitted)")
    else:
        debug_print(" (no lines matched requests/response/json/faasr_/open)")
    debug_print("--- end src hints ---")


class BlockBuilder:
    """
    Build a complete FaaSr block from a contract specification.

    The builder orchestrates the full pipeline:
    1. Writes contract.json to the block directory
    2. Validates contract against JSON schema
    3. Generates pytest tests from contract (with optional retry)
    4. Validates test coverage against contract
    5. Generates source implementation from contract + tests
    6. Iterates: static validation → pytest → regenerate source (up to max_source_iterations)
    7. Validates final block structure

    If pytest fails, the builder feeds error messages back to the source generator for fixes.
    """

    def __init__(
        self,
        llm: LLMClient,
        schema_path: Path | None = None,
        max_source_iterations: int = 3,
        retry_tests_once: bool = True,
    ) -> None:
        """
        Initialize the block builder.

        Args:
            llm: LLM client for generating tests and source code.
            schema_path: Optional path to contract_schema.json (auto-detects <repo>/schema/ if None).
            max_source_iterations: Maximum loops for source generation (static validation + pytest).
            retry_tests_once: If True, retry test generation once on coverage validation failure.
        """
        self._llm = llm
        self._schema_path = schema_path
        self._max_source_iterations = max_source_iterations
        self._retry_tests_once = retry_tests_once

    def build(
        self,
        contract: Contract,
        blocks_root: Path,
        repo_root: Path | None = None,
    ) -> BuildResult:
        """
        Build a block from contract: generate tests, source, validate, and run pytest.

        Creates blocks_root/<BlockName>/ with:
        - contract.json
        - tests/test_<function>.py + fixtures/
        - src/<function>.py

        The build process loops up to max_source_iterations times, regenerating source code
        when static validation or pytest fails. Each iteration includes:
        - Static validation (function signature, FaaSr API calls)
        - Pytest execution
        - Feedback to source generator with error details

        Args:
            contract: Contract specification for the block.
            blocks_root: Directory containing all block folders (e.g., repo/blocks).
            repo_root: Repository root (defaults to blocks_root parent).

        Returns:
            BuildResult with success status, paths, attempt count, and validation/test results.
        """
        if repo_root is None:
            repo_root = blocks_root.parent

        debug_print(
            "build start block_name=",
            contract.block_name,
            "function=",
            contract.function.name,
            "max_source_iterations=",
            self._max_source_iterations,
        )
        debug_print(
            "Set FAASR_BLOCKS_DEBUG=1 for extra diagnostics (HTTP mock vs response.text/json).",
        )

        block_path = blocks_root / contract.block_name
        block_path.mkdir(parents=True, exist_ok=True)
        (block_path / "src").mkdir(exist_ok=True)
        (block_path / "tests" / "fixtures").mkdir(parents=True, exist_ok=True)

        contract_path = block_path / "contract.json"
        contract_path.write_text(
            contract.model_dump_json(indent=2),
            encoding="utf-8",
        )

        schema = self._schema_path
        if schema is None:
            candidate = repo_root / "schema" / "contract_schema.json"
            if candidate.is_file():
                schema = candidate
        if schema is not None:
            cv = ContractValidator(schema)
            ok, msg = cv.validate_contract(contract_path)
            if not ok:
                return BuildResult(
                    success=False,
                    block_path=str(block_path),
                    message=f"Contract validation failed: {msg}",
                )

        fn = contract.function.name
        test_path = block_path / "tests" / f"test_{fn}.py"

        test_gen = TestGenerator(self._llm)
        test_gen.generate(contract, block_path, repo_root)
        debug_print("after test_gen tests at", test_path)

        tv = ContractTestCoverageValidator(self._llm)
        tval = tv.validate(contract, test_path)
        if not tval.ok and self._retry_tests_once:
            test_gen.generate(
                contract,
                block_path,
                repo_root,
                extra_instructions="Prior test-contract validation reported gaps:\n"
                + "\n".join(tval.errors),
            )
            tval = tv.validate(contract, test_path)

        if not tval.ok:
            return BuildResult(
                success=False,
                block_path=str(block_path),
                message="Test-contract alignment failed: " + "; ".join(tval.errors),
                test_contract_validation=tval,
            )

        debug_print("test-contract coverage ok")
        test_src = test_path.read_text(encoding="utf-8")
        src_gen = SourceCodeGenerator(self._llm)
        src_gen.generate(contract, block_path, repo_root, test_src, extra_instructions="")
        _debug_src_hints(block_path / "src" / f"{fn}.py")

        sv = StaticValidator()
        runner = TestRunner()
        last_test = None
        last_static: ValidationResult | None = None

        for attempt in range(1, self._max_source_iterations + 1):
            src_file = block_path / "src" / f"{fn}.py"
            debug_print("--- iteration", attempt, "/", self._max_source_iterations, "---")
            last_static = sv.validate(contract, src_file)
            debug_print(
                "static_validation ok=",
                last_static.ok,
                "errors=",
                last_static.errors,
                "warnings=",
                last_static.warnings,
            )
            if not last_static.ok:
                src_gen.generate(
                    contract,
                    block_path,
                    repo_root,
                    test_src,
                    extra_instructions="Static validation failed:\n"
                    + "\n".join(last_static.errors),
                )
                _debug_src_hints(src_file)
                continue

            last_test = runner.run_tests(block_path, repo_root)
            debug_print(
                "pytest passed=",
                last_test.passed,
                "exit_code=",
                last_test.exit_code,
                "summary=",
                last_test.summary_line,
            )
            if not last_test.passed and debug_enabled():
                debug_print("pytest stdout (tail 6000 chars):")
                debug_print((last_test.stdout or "")[-6000:])
                debug_print("pytest stderr (tail 2000 chars):")
                debug_print((last_test.stderr or "")[-2000:])

            if last_test.passed:
                bv = BlockValidator()
                ok, errors = bv.validate_structure(block_path)
                if not ok:
                    return BuildResult(
                        success=False,
                        block_path=str(block_path),
                        message="Block structure invalid: " + "; ".join(errors),
                        attempts=attempt,
                        test_result=last_test,
                        static_validation=last_static,
                        test_contract_validation=tval,
                    )
                return BuildResult(
                    success=True,
                    block_path=str(block_path),
                    message="Block built and tests passed.",
                    attempts=attempt,
                    test_result=last_test,
                    static_validation=last_static,
                    test_contract_validation=tval,
                )

            fail_text = (
                "Pytest failed. Fix implementation only.\n\n"
                + f"exit_code={last_test.exit_code}\n"
                + f"summary: {last_test.summary_line}\n\n"
                + "stdout:\n"
                + last_test.stdout
                + "\n\nstderr:\n"
                + last_test.stderr
                + _pytest_remediation_hints(last_test.stdout or "")
            )
            src_gen.generate(
                contract,
                block_path,
                repo_root,
                test_src,
                extra_instructions=fail_text,
            )
            _debug_src_hints(src_file)

        return BuildResult(
            success=False,
            block_path=str(block_path),
            message="Exceeded max source iterations; tests still failing or static validation stuck.",
            attempts=self._max_source_iterations,
            test_result=last_test,
            static_validation=last_static,
            test_contract_validation=tval,
        )
