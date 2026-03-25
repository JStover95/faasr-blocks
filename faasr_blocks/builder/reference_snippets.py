"""Load reference documentation snippets for LLM prompts.

This module provides helper functions to read FaaSr reference documentation and example code
from the reference/ directory, with automatic truncation for large files.
"""

from __future__ import annotations

from pathlib import Path


def read_if_exists(repo_root: Path, *parts: str, max_chars: int | None = 24_000) -> str:
    """
    Read a file from the reference directory, with optional truncation.

    Args:
        repo_root: Repository root path.
        *parts: Path components to join (e.g., "reference", "faasr-docs", "docs", "py_api.md").
        max_chars: Maximum characters to read before truncating (None for no limit).

    Returns:
        File contents (possibly truncated with marker), or a placeholder message if missing.
    """
    p = repo_root.joinpath(*parts)
    if not p.is_file():
        try:
            rel = p.relative_to(repo_root)
        except ValueError:
            rel = p
        return f"(missing reference file: {rel})"
    text = p.read_text(encoding="utf-8", errors="replace")
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + "\n\n... [truncated] ...\n"
    return text


def default_snippets(repo_root: Path) -> dict[str, str]:
    """
    Load standard reference documentation snippets for LLM prompts.

    Args:
        repo_root: Repository root path.

    Returns:
        Dictionary mapping snippet keys to documentation text:
        - py_api: Python API reference (faasr_get_file, faasr_put_file, etc.)
        - functions_md: Function development guide
        - conditional_md: Conditional branching documentation
        - credentials_md: Secrets management guide
        - compute_sum_py: Tutorial example Python function
    """
    """Key -> text blocks to embed in prompts."""
    return {
        "py_api": read_if_exists(repo_root, "reference", "faasr-docs", "docs", "py_api.md"),
        "functions_md": read_if_exists(
            repo_root, "reference", "faasr-docs", "docs", "functions.md", max_chars=12_000
        ),
        "conditional_md": read_if_exists(
            repo_root, "reference", "faasr-docs", "docs", "conditional.md", max_chars=8_000
        ),
        "credentials_md": read_if_exists(
            repo_root, "reference", "faasr-docs", "docs", "credentials.md", max_chars=8_000
        ),
        "compute_sum_py": read_if_exists(
            repo_root, "reference", "faasr-functions", "tutorial", "compute_sum.py"
        ),
    }


def example_block_test(repo_root: Path) -> str:
    """
    Load the GetWeatherData example test as a pattern for the test generator.

    Args:
        repo_root: Repository root path.

    Returns:
        Full content of blocks/GetWeatherData/tests/test_get_weather_data.py,
        or a placeholder if not found.
    """
    ex = repo_root / "blocks" / "GetWeatherData" / "tests" / "test_get_weather_data.py"
    if ex.is_file():
        return ex.read_text(encoding="utf-8")
    return "(no example test file in repo)"
