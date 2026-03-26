"""Validate on-disk layout of a block directory."""

from __future__ import annotations

from pathlib import Path


class BlockValidator:
    """Ensure blocks/<Name>/ has contract, src, and tests."""

    REQUIRED_ENTRIES = ("contract.json", "src", "tests")

    @classmethod
    def validate_structure(cls, block_path: Path) -> tuple[bool, list[str]]:
        """
        Validate that a block directory has the required structure.

        Returns (is_valid, list_of_errors).
        """
        # Validate that the block path is a directory
        errors: list[str] = []
        if not block_path.is_dir():
            return False, [f"Not a directory: {block_path}"]

        # Validate that the required entries exist
        for required in cls.REQUIRED_ENTRIES:
            path = block_path / required
            if not path.exists():
                errors.append(f"Missing required: {required}")

        # Validate that the src directory exists and has Python files
        src_dir = block_path / "src"
        if src_dir.is_dir() and not any(src_dir.glob("*.py")):
            errors.append("src/ directory has no Python files")

        # Validate that the tests directory exists and has test files
        tests_dir = block_path / "tests"
        if tests_dir.is_dir() and not any(tests_dir.glob("test_*.py")):
            errors.append("tests/ directory has no test files")

        # Return the validation result
        return len(errors) == 0, errors
