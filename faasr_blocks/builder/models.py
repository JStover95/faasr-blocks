"""Result types for the block builder pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """
    Outcome of a validation step (static AST analysis or LLM-based contract coverage check).

    Attributes:
        ok: True if validation passed, False otherwise.
        errors: List of validation errors that must be fixed.
        warnings: List of non-blocking issues or suggestions.
    """

    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def success(cls) -> ValidationResult:
        """
        Create a successful validation result with no errors or warnings.

        Returns:
            ValidationResult with ok=True.
        """
        return cls(ok=True)

    @classmethod
    def failure(cls, errors: list[str], warnings: list[str] | None = None) -> ValidationResult:
        """
        Create a failed validation result with specified errors.

        Args:
            errors: List of validation error messages.
            warnings: Optional list of warning messages.

        Returns:
            ValidationResult with ok=False and the provided errors/warnings.
        """
        return cls(ok=False, errors=list(errors), warnings=list(warnings or []))


@dataclass
class TestResult:
    """
    Outcome of running pytest on a block's test suite.

    Attributes:
        passed: True if all tests passed (exit_code == 0).
        exit_code: Pytest exit code (0=all passed, 1=failures, 2=collection error).
        stdout: Captured standard output from pytest.
        stderr: Captured standard error from pytest.
        summary_line: Extracted pytest summary (e.g., "5 passed in 0.12s" or "1 failed, 2 passed").
    """

    passed: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    summary_line: str = ""


@dataclass
class BuildResult:
    """
    Final outcome of the block building process from :meth:`BlockBuilder.build` (no arguments).

    Attributes:
        success: True if block was successfully built and all tests passed.
        block_path: Absolute path to the generated block directory.
        message: Human-readable status message describing the outcome.
        attempts: Number of source code generation iterations attempted.
        test_result: Final pytest result (None if pytest never ran).
        static_validation: Final static validation result (None if not reached).
        test_contract_validation: Test coverage validation result (None if not reached).
    """

    success: bool
    block_path: str = ""
    message: str = ""
    attempts: int = 0
    test_result: TestResult | None = None
    static_validation: ValidationResult | None = None
    test_contract_validation: ValidationResult | None = None
