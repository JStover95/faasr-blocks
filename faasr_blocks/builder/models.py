"""Result types for the block builder pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Outcome of static or LLM-based validation."""

    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def success(cls) -> ValidationResult:
        return cls(ok=True)

    @classmethod
    def failure(cls, errors: list[str], warnings: list[str] | None = None) -> ValidationResult:
        return cls(ok=False, errors=list(errors), warnings=list(warnings or []))


@dataclass
class TestResult:
    """Outcome of running pytest on a block."""

    passed: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    summary_line: str = ""


@dataclass
class BuildResult:
    """Outcome of :meth:`BlockBuilder.build`."""

    success: bool
    block_path: str = ""
    message: str = ""
    attempts: int = 0
    test_result: TestResult | None = None
    static_validation: ValidationResult | None = None
    test_contract_validation: ValidationResult | None = None
