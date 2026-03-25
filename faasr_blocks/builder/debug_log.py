"""Opt-in debug logging for the block builder (share logs with collaborators)."""

from __future__ import annotations

import os


def debug_enabled() -> bool:
    """
    Check if debug mode is enabled via the FAASR_BLOCKS_DEBUG environment variable.

    Returns:
        True if FAASR_BLOCKS_DEBUG is set to "1", "true", "yes", or "on" (case-insensitive).
    """
    v = os.environ.get("FAASR_BLOCKS_DEBUG", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def debug_print(*args: object, **kwargs: object) -> None:
    """
    Print debug information prefixed with [faasr-blocks] if debug mode is enabled.

    Only prints when :func:`debug_enabled` returns True. All output is flushed immediately
    to ensure logs appear in order with subprocess output.

    Args:
        *args: Positional arguments passed to print().
        **kwargs: Keyword arguments passed to print().
    """
    if debug_enabled():
        print("[faasr-blocks]", *args, **kwargs, flush=True)
