"""Orchestrate test generation, validation, implementation, and pytest."""

from __future__ import annotations

from pathlib import Path

from faasr_blocks.builder.block_context import BlockContext
from faasr_blocks.builder.debug_log import debug_enabled, debug_print
from faasr_blocks.builder.models import BuildResult, TestResult, ValidationResult
from faasr_blocks.builder.source_generator import SourceCodeGenerator
from faasr_blocks.builder.static_validator import StaticValidator
from faasr_blocks.builder.test_generator import TestGenerator
from faasr_blocks.builder.test_runner import TestRunner
from faasr_blocks.builder.test_validator import ContractTestCoverageValidator
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
    1. Validates contract.json on disk against JSON schema
    2. Generates pytest tests from contract (with optional retry)
    3. Validates test coverage against contract
    4. Generates source implementation from contract + tests
    5. Iterates: static validation → pytest → regenerate source (up to max_source_iterations)
    6. Validates final block structure

    If pytest fails, the builder feeds error messages back to the source generator for fixes.

    Callers construct generators and validators and inject them; the builder only orchestrates.
    """

    def __init__(
        self,
        context: BlockContext,
        test_generator: TestGenerator,
        test_coverage_validator: ContractTestCoverageValidator,
        source_generator: SourceCodeGenerator,
        max_source_iterations: int = 3,
        retry_tests_once: bool = True,
    ) -> None:
        """
        Initialize the block builder.

        Args:
            context: Block paths, contract, schema path, and repo layout.
            test_generator: Generates pytest files under the block directory.
            test_coverage_validator: LLM check that tests cover the contract.
            source_generator: Generates implementation under src/.
            max_source_iterations: Maximum loops for source generation (static validation + pytest).
            retry_tests_once: If True, retry test generation once on coverage validation failure.
        """
        self._context = context
        self._test_generator = test_generator
        self._test_coverage_validator = test_coverage_validator
        self._source_generator = source_generator
        self._max_source_iterations = max_source_iterations
        self._retry_tests_once = retry_tests_once
        self._static_validator = StaticValidator(context)
        self._test_runner = TestRunner(context)
        self._block_validator = BlockValidator()

    def _run_source_iteration(
        self,
        attempt: int,
        test_src: str,
        test_validation: ValidationResult,
    ) -> tuple[BuildResult | None, TestResult | None, ValidationResult | None]:
        """
        One static-validation / pytest / optional source-regeneration cycle.

        Returns:
            (early_result, last_test, last_static).
        """
        # Pull context values
        block_path = self._context.block_path
        src_file = self._context.src_file

        debug_print("--- iteration", attempt, "/", self._max_source_iterations, "---")

        # 1. Run static validation
        last_static = self._static_validator.validate()

        debug_print(
            "static_validation ok=",
            last_static.ok,
            "errors=",
            last_static.errors,
            "warnings=",
            last_static.warnings,
        )

        if not last_static.ok:
            # If static validation failed, re-generate source code with error instructions and exit early
            self._source_generator.generate(
                test_src,
                extra_instructions="Static validation failed:\n" + "\n".join(last_static.errors),
            )

            _debug_src_hints(src_file)

            return None, None, last_static

        # 2. Run tests
        last_test = self._test_runner.run_tests()

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

        if not last_test.passed:
            # If pytest failed, re-generate source code with error instructions and exit early
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
            self._source_generator.generate(
                test_src,
                extra_instructions=fail_text,
            )

            _debug_src_hints(src_file)

            return None, last_test, last_static

        # 3. Validate the block's directory structure
        ok, errors = self._block_validator.validate_structure(block_path)

        if not ok:
            # If the block's directory structure is invalid, return an error and exit early
            return (
                BuildResult(
                    success=False,
                    block_path=str(block_path),
                    message="Block structure invalid: " + "; ".join(errors),
                    attempts=attempt,
                    test_result=last_test,
                    static_validation=last_static,
                    test_contract_validation=test_validation,
                ),
                last_test,
                last_static,
            )

        # All validation checks passed, return a success result
        return (
            BuildResult(
                success=True,
                block_path=str(block_path),
                message="Block built and tests passed.",
                attempts=attempt,
                test_result=last_test,
                static_validation=last_static,
                test_contract_validation=test_validation,
            ),
            last_test,
            last_static,
        )

    def build(self) -> BuildResult:
        """
        Build a block from contract: generate tests, source, validate, and run pytest.

        Uses :class:`BlockContext` supplied at construction. Expects ``block_path`` to exist
        and contain ``contract.json``.

        Returns:
            BuildResult with success status, paths, attempt count, and validation/test results.
        """
        # Pull context values
        contract = self._context.contract
        block_path = self._context.block_path
        test_path = self._context.test_path
        contract_path = self._context.contract_path
        schema_path = self._context.schema_path

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

        # 1. Validate that the contract is valid
        # TODO: Contract validation will eventually be moved to the contract generation agent.
        cv = ContractValidator(schema_path)
        ok, msg = cv.validate_contract(contract_path)
        if not ok:
            return BuildResult(
                success=False,
                block_path=str(block_path),
                message=f"Contract validation failed: {msg}",
            )

        # 2. Generate tests
        self._test_generator.generate()

        debug_print("after test_gen tests at", test_path)

        # 3. Validate that the tests cover the contract
        test_validation = self._test_coverage_validator.validate()

        # 4. Retry test generation if needed and retry tests once is set
        if not test_validation.ok and self._retry_tests_once:
            self._test_generator.generate(
                extra_instructions="Prior test-contract validation reported gaps:\n"
                + "\n".join(test_validation.errors),
            )
            test_validation = self._test_coverage_validator.validate()

        if not test_validation.ok:
            return BuildResult(
                success=False,
                block_path=str(block_path),
                message="Test-contract alignment failed: " + "; ".join(test_validation.errors),
                test_contract_validation=test_validation,
            )

        debug_print("test-contract coverage ok")

        # 5. Generate source code
        test_src = test_path.read_text(encoding="utf-8")
        self._source_generator.generate(test_src, extra_instructions="")

        _debug_src_hints(self._context.src_file)

        # 6. Run source code generation iterations until tests pass

        # Test and static validation results to return
        last_test: TestResult | None = None
        last_static: ValidationResult | None = None
        result: BuildResult | None = None

        for attempt in range(1, self._max_source_iterations + 1):
            result, last_test, last_static = self._run_source_iteration(
                attempt,
                test_src,
                test_validation,
            )

            # If we received a result, exit early
            if result is not None:
                break

        # Return the build result or a failure
        if result is not None:
            return result

        return BuildResult(
            success=False,
            block_path=str(block_path),
            message="Exceeded max source iterations; tests still failing or static validation stuck.",
            attempts=self._max_source_iterations,
            test_result=last_test,
            static_validation=last_static,
            test_contract_validation=test_validation,
        )
