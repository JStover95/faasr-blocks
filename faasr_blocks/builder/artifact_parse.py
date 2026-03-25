"""Parse multi-file outputs from LLM prompts."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

_FILE_HEADER = re.compile(r"^###\s*FILE:\s*(\S+)\s*$", re.MULTILINE)


def _first_fenced_block(after_header: str) -> tuple[str, int] | None:
    """Return (body, end_index) for first ``` ... ``` in *after_header*."""
    start = after_header.find("```")
    if start < 0:
        return None
    nl = after_header.find("\n", start)
    if nl < 0:
        return None
    close = after_header.find("```", nl + 1)
    if close < 0:
        return None
    body = after_header[nl + 1 : close]
    if body.endswith("\n"):
        body = body[:-1]
    return body, close + 3


def parse_marked_files(text: str) -> dict[str, str]:
    """
    Extract multiple files from LLM output using marked headers and fenced code blocks.

    Expected format in the LLM response:

        ### FILE: relative/path.ext
        ```python
        ...
        ```

        ### FILE: another/file.json
        ```json
        {...}
        ```

    Args:
        text: Full LLM response text.

    Returns:
        Dictionary mapping normalized relative POSIX paths to file contents.

    Raises:
        ValueError: If a FILE header is found without a following fenced code block.
    """
    files: dict[str, str] = {}
    for m in _FILE_HEADER.finditer(text):
        rel = str(PurePosixPath(m.group(1).strip()))
        tail = text[m.end() :]
        parsed = _first_fenced_block(tail)
        if not parsed:
            raise ValueError(f"No fenced code block found after FILE header for {rel!r}")
        body, _ = parsed
        files[rel] = body
    return files


def extract_single_python_module(text: str) -> str:
    """
    Extract Python code from a single fenced block, or return text as-is if no fence found.

    Fallback parser when the LLM doesn't use marked FILE: headers. Looks for a single
    ```python or ``` block and extracts its body.

    Args:
        text: LLM response text.

    Returns:
        Code body from fenced block if found, otherwise stripped text.
    """
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if m:
        body = m.group(1)
        if body.endswith("\n"):
            body = body[:-1]
        return body.strip()
    return text.strip()
