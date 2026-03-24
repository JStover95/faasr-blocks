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
    If pytest output matches known failure modes, add explicit instructions for the LLM.

    Common case: tests mock ``requests.Response`` with ``mock_resp.json.return_value = {...}`` but
    implementation uses ``response.text``; ``MagicMock.text`` is not a ``str`` for ``file.write``.
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
    """Print lines that show how HTTP / FaaSr APIs are used (mock mismatch diagnosis)."""
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
    """Build ``blocks/<BlockName>/`` from a :class:`Contract` using an :class:`LLMClient`."""

    def __init__(
        self,
        llm: LLMClient,
        schema_path: Path | None = None,
        max_source_iterations: int = 3,
        retry_tests_once: bool = True,
    ) -> None:
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
