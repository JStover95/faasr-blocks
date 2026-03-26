# ruff: noqa: E402

"""CLI for interactive FaaSr Blocks orchestrator agent (Phase 4a PoC).

Interactive command-line session using prompt_toolkit. Does not yet invoke
discovery, contract generation, or the block builder.

Usage:
    faasr-blocks-agent [--debug] [--multiline] [--history-file PATH]

Environment (all required at startup per product boundary):
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
    FAASR_S3_ENDPOINT, FAASR_S3_ACCESS_KEY, FAASR_S3_SECRET_KEY, FAASR_S3_BUCKET
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import faasr_blocks
from faasr_blocks.builder.config import load_llm_env_config, load_s3_env_config
from faasr_blocks.orchestrator.commands import StubHandler
from faasr_blocks.orchestrator.repl import InteractiveREPL
from faasr_blocks.orchestrator.session import OrchestratorSession


def _package_repo_root() -> Path:
    """Repository root for the faasr-blocks package (parent of ``faasr_blocks``)."""
    return Path(faasr_blocks.__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    """
    Entry point for ``faasr-blocks-agent``.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv`` if None).

    Returns:
        0 after normal REPL exit, 2 if required configuration is missing.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Interactive FaaSr Blocks agent (Phase 4a). "
            "Requires OpenAI-compatible and S3 env vars; see module docstring."
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print diagnostic context to stderr (repo root, model, S3 bucket).",
    )
    parser.add_argument(
        "--multiline",
        action="store_true",
        help="Allow multiline input; submit with Esc+Enter (Enter inserts newline).",
    )
    parser.add_argument(
        "--history-file",
        type=Path,
        default=None,
        help="Optional path for prompt_toolkit FileHistory (created if missing).",
    )
    args = parser.parse_args(argv)

    try:
        llm_cfg = load_llm_env_config()
        s3_cfg = load_s3_env_config()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    repo_root = _package_repo_root()
    session = OrchestratorSession()
    handler = StubHandler()
    repl = InteractiveREPL(
        session,
        handler,
        repo_root=repo_root,
        llm_config=llm_cfg,
        s3_config=s3_cfg,
        history_file=args.history_file,
        multiline=args.multiline,
        debug=args.debug,
    )
    repl.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
