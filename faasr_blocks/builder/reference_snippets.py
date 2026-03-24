"""Load reference documentation paths for LLM prompts."""

from __future__ import annotations

from pathlib import Path


def read_if_exists(repo_root: Path, *parts: str, max_chars: int | None = 24_000) -> str:
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
    ex = repo_root / "blocks" / "GetWeatherData" / "tests" / "test_get_weather_data.py"
    if ex.is_file():
        return ex.read_text(encoding="utf-8")
    return "(no example test file in repo)"
