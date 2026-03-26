# ruff: noqa: E402

"""CLI for interactive FaaSr Blocks orchestrator agent (Phase 4).

Interactive command-line session using prompt_toolkit. Runs contract planning,
optional clarification, approval, semantic discovery, and block builds.

Usage:
    faasr-blocks-agent [--debug] [--multiline] [--history-file PATH] [--stub]

Environment (all required at startup unless ``--stub``):
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
from faasr_blocks.builder.config import (
    LLMEnvConfig,
    S3EnvConfig,
    load_llm_env_config,
    load_s3_env_config,
)
from faasr_blocks.builder.llm import OpenAIChatLLM
from faasr_blocks.discovery.embedding import OpenAIEmbeddingClient
from faasr_blocks.discovery.storage import S3EmbeddingStore
from faasr_blocks.orchestrator.commands import OrchestratorCommandHandler, StubHandler
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
            "Interactive FaaSr Blocks agent (Phase 4). "
            "Requires OpenAI-compatible and S3 env vars unless --stub; see module docstring."
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
    parser.add_argument(
        "--stub",
        action="store_true",
        help="Use stub handler only (no LLM/S3 pipeline); for UI testing without API keys.",
    )
    args = parser.parse_args(argv)

    repo_root = _package_repo_root()
    schema_path = (repo_root / "schema" / "contract_schema.json").resolve()

    if args.stub:
        llm_cfg = LLMEnvConfig(api_key="(stub)", base_url="(stub)", model="(stub)")
        s3_cfg = S3EnvConfig(
            endpoint="(stub)",
            access_key="(stub)",
            secret_key="(stub)",
            bucket="(stub)",
        )
        session = OrchestratorSession()
        handler: StubHandler | OrchestratorCommandHandler = StubHandler()
    else:
        try:
            llm_cfg = load_llm_env_config()
            s3_cfg = load_s3_env_config()
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2

        if not schema_path.is_file():
            print(
                f"Contract schema not found at {schema_path}. "
                "Ensure schema/contract_schema.json exists in the faasr-blocks repo.",
                file=sys.stderr,
            )
            return 2

        llm = OpenAIChatLLM(
            api_key=llm_cfg.api_key,
            base_url=llm_cfg.base_url,
            model=llm_cfg.model,
        )
        embedding_client = OpenAIEmbeddingClient(
            api_key=llm_cfg.api_key,
            base_url=llm_cfg.base_url,
            model="text-embedding-3-small",
        )
        embedding_store = S3EmbeddingStore(
            endpoint=s3_cfg.endpoint,
            access_key=s3_cfg.access_key,
            secret_key=s3_cfg.secret_key,
            bucket=s3_cfg.bucket,
        )
        session = OrchestratorSession()
        handler = OrchestratorCommandHandler(
            llm=llm,
            embedding_client=embedding_client,
            embedding_store=embedding_store,
            repo_root=repo_root,
            schema_path=schema_path,
        )
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

    try:
        repl.run()
    finally:
        if isinstance(handler, OrchestratorCommandHandler):
            handler.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
