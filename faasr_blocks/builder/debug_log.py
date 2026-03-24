"""Opt-in debug logging for the block builder (share logs with collaborators)."""

from __future__ import annotations

import os


def debug_enabled() -> bool:
    v = os.environ.get("FAASR_BLOCKS_DEBUG", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def debug_print(*args: object, **kwargs: object) -> None:
    if debug_enabled():
        print("[faasr-blocks]", *args, **kwargs, flush=True)
