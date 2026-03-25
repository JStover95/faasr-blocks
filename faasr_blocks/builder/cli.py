"""CLI for building a block from contract.json (Phase 2 PoC).

Command-line interface for the block builder. Takes a contract.json path and generates
a complete block with tests and implementation using an OpenAI-compatible LLM.

Usage:
    faasr-blocks-build path/to/contract.json

Environment:
    OPENAI_API_KEY: Required. API key for LLM access.
    OPENAI_BASE_URL: Optional. API endpoint (default: https://api.openai.com/v1).
    OPENAI_MODEL: Optional. Model name (default: gpt-4o-mini).
    FAASR_BLOCKS_DEBUG: Optional. Set to "1" for verbose debug output.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from faasr_blocks.builder.block_builder import BlockBuilder
from faasr_blocks.builder.llm import OpenAIChatLLM
from faasr_blocks.models.contract import Contract


def _package_repo_root() -> Path:
    """
    Find the repository root by locating the installed faasr_blocks package.

    Returns:
        Path to the parent directory of the faasr_blocks package (the repo root).
    """
    import faasr_blocks

    return Path(faasr_blocks.__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point for faasr-blocks-build command.

    Parses arguments, loads the contract, initializes the LLM client, and invokes BlockBuilder.
    Displays progress and results to stdout/stderr.

    Args:
        argv: Command-line arguments (defaults to sys.argv if None).

    Returns:
        Exit code: 0 on success, 1 on build failure, 2 on usage/setup errors.
    """
    parser = argparse.ArgumentParser(
        description="Generate tests and source for a FaaSr block from contract.json (requires OPENAI_API_KEY).",
    )
    parser.add_argument(
        "contract",
        type=Path,
        help="Path to contract.json (existing block dir or standalone file).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="FaaSr-Blocks repository root (default: parent of installed faasr_blocks package).",
    )
    parser.add_argument(
        "--blocks-root",
        type=Path,
        default=None,
        help="Directory containing block folders (default: <repo-root>/blocks).",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="Path to contract_schema.json (default: <repo-root>/schema/contract_schema.json).",
    )
    parser.add_argument(
        "--max-source-iterations",
        type=int,
        default=3,
        help="Max fix-up loops for static validation / pytest failures.",
    )
    args = parser.parse_args(argv)

    repo_root = (args.repo_root or _package_repo_root()).resolve()
    blocks_root = (args.blocks_root or (repo_root / "blocks")).resolve()
    contract_path = args.contract.resolve()

    if not contract_path.is_file():
        print(f"Contract file not found: {contract_path}", file=sys.stderr)
        return 2

    contract = Contract.from_json_path(contract_path)
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "OPENAI_API_KEY is not set. Export it or use a compatible API key for OpenAIChatLLM.",
            file=sys.stderr,
        )
        return 2

    llm = OpenAIChatLLM()
    builder = BlockBuilder(
        llm,
        schema_path=args.schema.resolve() if args.schema else None,
        max_source_iterations=args.max_source_iterations,
    )

    print(f"Repo root: {repo_root}")
    print(f"Blocks root: {blocks_root}")
    print(f"Building block: {contract.block_name}")
    try:
        result = builder.build(contract, blocks_root, repo_root=repo_root)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2

    print()
    if result.success:
        print(result.message)
        print(f"Block path: {result.block_path}")
        if result.test_result:
            print(f"Pytest: {result.test_result.summary_line}")
        return 0

    print(f"FAILED: {result.message}", file=sys.stderr)
    if result.test_contract_validation and not result.test_contract_validation.ok:
        for e in result.test_contract_validation.errors:
            print(f"  test-contract: {e}", file=sys.stderr)
    if result.static_validation and not result.static_validation.ok:
        for e in result.static_validation.errors:
            print(f"  static: {e}", file=sys.stderr)
    if result.test_result and not result.test_result.passed:
        print(result.test_result.stdout[-4000:], file=sys.stderr)
        print(result.test_result.stderr[-2000:], file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
